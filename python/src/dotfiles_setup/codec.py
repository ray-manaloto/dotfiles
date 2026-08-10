# Copyright (c) 2026 Raymond Manaloto
"""The one module owning msgspec's encode and decode hooks (#675).

msgspec is the project's single model system (#669). It handles the types a
JSON document is made of, plus a documented set it converts for you —
``datetime``, ``uuid.UUID``, ``decimal.Decimal`` all encode natively. Anything
else goes through a **hook**, and msgspec's hooks are ``enc_hook``/``dec_hook``
keyword arguments to each ``encode``/``decode`` call rather than a global
registration.

That per-call design is why this module exists **from the outset** rather than
being extracted later. Every call site that passes msgspec its own hook owns a
copy of the conversion table, and copies drift; by the time a second type needs
converting there is no single place to add it. Retrofitting means finding every
call, which is the situation #669 declined to walk into.

``pathlib.Path`` is the type that forces the issue, and it is unsupported in
**both** directions. Measured against msgspec 0.21.1, control-armed against the
three types above (all of which encode unaided, so the probe discriminates)::

    >>> msgspec.json.encode(pathlib.Path("/tmp/x"))
    TypeError: Encoding objects of type PosixPath is unsupported
    >>> msgspec.json.decode(b'"/tmp/x"', type=pathlib.Path)
    ValidationError: Expected `Path`, got `str`

The decode half is the one worth internalising. It raises only because the
annotation says ``Path``; a field annotated ``str`` accepts the value happily
and hands the caller a string that behaves like a path right up until something
calls ``.parent`` on it.

Why a registry rather than an ``isinstance`` chain
--------------------------------------------------

:func:`register` exists so the *next* unsupported type is a one-line
declaration instead of an edit to :func:`enc_hook`. A hook that grows a branch
per type is still "one place" by file count and stops being one by any measure
that matters — and the branches accumulate in the order people happened to need
them, which is the shape nobody can review.

The lookup walks the **method resolution order**, not exact identity, because
``Path()`` never instantiates ``Path``: on this platform it returns
``PosixPath``, which is what msgspec's own error names. A registry keyed on the
exact type would therefore miss every real path while passing a test written
against ``PurePath``.

Failing loudly
--------------

An unregistered type raises :class:`UnsupportedTypeError`, which subclasses
``NotImplementedError`` — the exception msgspec's own documentation tells hooks
to raise — and carries the offending type as an attribute so a caller can branch
on it without parsing a message.

The alternative worth naming, because it is the tempting one: falling back to
``str(obj)``. It never fails, since every object has a ``__str__``, so an
unregistered type would encode as ``"<Foo object at 0x10a>"``, round-trip to
nothing, and surface as corrupt data a long way from here. That is precisely the
"silently degrading" this module's acceptance criterion forbids.
"""

from __future__ import annotations

import enum
import typing
from collections.abc import Callable
from pathlib import PurePath
from typing import Any

import msgspec
import msgspec.inspect

__all__ = [
    "AlreadyNativeError",
    "Format",
    "UnsupportedTypeError",
    "dec_hook",
    "decode",
    "enc_hook",
    "encode",
    "register",
    "unregister",
]

#: Turns an unsupported instance into something msgspec can encode.
_Encoder = Callable[[Any], Any]

#: Rebuilds an instance from an encoded value. Takes the TARGET TYPE as well as
#: the value, mirroring msgspec's own ``dec_hook(type, obj)`` — and for the same
#: reason. The annotation is information the decoder genuinely needs and the
#: encoder cannot have: encoding sees a concrete instance, while decoding is
#: told which of a family of types to produce. Seeding ``PurePath -> Path``
#: instead cost a real defect (review F6): ``PureWindowsPath`` encoded fine and
#: then failed to decode, because the decoder ignored what it was asked for.
_Decoder = Callable[[type, Any], Any]


class Format(enum.Enum):
    """The wire formats this project encodes to.

    ``JSON`` is the default and the one #669 chose for records: it is what the
    devcontainer CLI already emits, it is what the log-scanning gate consumes,
    and it can be read with ordinary tools during an incident. ``MSGPACK`` is
    the compact binary form msgspec produces **from the same definitions**, so
    reaching for it never costs a second model.
    """

    JSON = "json"
    MSGPACK = "msgpack"


def _unknown_format(fmt: object) -> str:
    """The message for a format outside :class:`Format`."""
    supported = ", ".join(f.name for f in Format)
    return f"unknown format {fmt!r}: expected one of {supported}"


class UnsupportedTypeError(NotImplementedError):
    """A type reached the codec with no registered conversion.

    Subclasses ``NotImplementedError`` because that is what msgspec documents a
    hook should raise to say "not mine" — so code following msgspec's own docs
    keeps working — while :attr:`offending_type` gives a caller somewhere to
    read the answer from other than the message text.
    """

    def __init__(self, offending_type: type, direction: str) -> None:
        """Record which type failed, and which way it was travelling.

        Args:
            offending_type: The type with no registered conversion.
            direction: ``"encode"`` or ``"decode"`` — the two hooks fail for
                different reasons and the fix differs, so the message says
                which one was asked.
        """
        self.offending_type = offending_type
        self.direction = direction
        super().__init__(
            f"cannot {direction} {offending_type.__module__}."
            f"{offending_type.__qualname__}: msgspec has no native support and "
            f"dotfiles_setup.codec has no registered conversion. Add one with "
            f"codec.register({offending_type.__qualname__}, encode=..., decode=...) "
            f"rather than calling msgspec directly"
        )


class AlreadyNativeError(ValueError):
    """:func:`register` was asked to convert a type msgspec already handles.

    Refused rather than accepted, because accepting it does **nothing**:
    msgspec only calls a hook for types it cannot handle itself, so a
    registration for ``Decimal`` or ``datetime`` is never consulted. Measured
    before this guard existed — ``register(Decimal, encode=float, …)`` followed
    by ``encode(Decimal("1.50"))`` still produced ``b'"1.50"'``, a JSON string,
    with ``float`` never called.

    That is the module's own "silently degrading" failure mode occurring on its
    extension seam: no error, no effect, and a wire form that is not what the
    caller asked for. Someone registering it wants a different encoding and has
    to be told they cannot get one this way.
    """

    def __init__(self, target: type, native: str) -> None:
        """Name the type and what msgspec already calls it.

        Args:
            target: The type that was offered for registration.
            native: msgspec's own name for how it handles that type.
        """
        self.target = target
        self.native = native
        super().__init__(
            f"{target.__qualname__} is already handled natively by msgspec "
            f"({native}), so a registered conversion would never be called — "
            f"msgspec only invokes a hook for types it cannot encode itself. "
            f"To change how it is serialized, wrap it in a type msgspec does "
            f"not know, or annotate the field with msgspec's own controls"
        )


def _native_handling(target: type) -> str | None:
    """Msgspec's own name for how it handles ``target``, or ``None``.

    ``msgspec.inspect.type_info`` reports ``CustomType`` for anything msgspec
    has no built-in support for, and a specific class otherwise — verified
    across ``Decimal``/``datetime``/``UUID``/``int``/``str`` (all specific) and
    ``Path``/``PurePath``/an unknown class (all ``CustomType``). Asking msgspec
    beats keeping our own list of what it supports, which would go stale the
    first time it adds a type.
    """
    try:
        info = msgspec.inspect.type_info(target)
    except TypeError, NotImplementedError:
        return None
    if isinstance(info, msgspec.inspect.CustomType):
        return None
    return type(info).__name__


#: Registered conversions, keyed by the base type an instance must be an
#: instance of. Seeded with the one type #675 exists for; every later entry is
#: a :func:`register` call, which is the whole point of the seam.
#:
#: The decoder is ``target(value)``, not ``Path(value)``: the annotation decides
#: which path flavour to build, so a ``PureWindowsPath`` field decodes to a
#: ``PureWindowsPath``.
_ENCODERS: dict[type, _Encoder] = {PurePath: str}
_DECODERS: dict[type, _Decoder] = {PurePath: lambda target, value: target(value)}


def register(
    target: type,
    *,
    encode: _Encoder,
    decode: _Decoder,
) -> None:
    """Teach the codec a type, in both directions at once.

    Both directions are required rather than optional because a half-registered
    type is the silent-corruption case: it would encode cleanly and decode to
    whatever primitive it was stored as, so the loss appears at read time in a
    different process.

    Args:
        target: The base type to match instances and annotations against.
            Subclasses resolve through it, so registering ``PurePath`` covers
            ``PosixPath`` and ``WindowsPath``.
        encode: Converts an instance to something msgspec can already encode.
        decode: Rebuilds an instance, given the annotated type and the encoded
            value — the same shape as msgspec's ``dec_hook``.

    Raises:
        AlreadyNativeError: msgspec handles ``target`` itself, so the
            registration would never be consulted.
    """
    native = _native_handling(target)
    if native is not None:
        raise AlreadyNativeError(target, native)
    _ENCODERS[target] = encode
    _DECODERS[target] = decode


def unregister(target: type) -> None:
    """Remove a registration. Chiefly for tests that add a temporary one.

    Args:
        target: The base type passed to :func:`register`.
    """
    _ENCODERS.pop(target, None)
    _DECODERS.pop(target, None)


def _runtime_class(candidate: object) -> type | None:
    """The class behind ``candidate``, unwrapping a parametrized generic.

    ``dec_hook`` receives the **annotation**, and an annotation is not always a
    class: ``Box[int]`` is a ``typing._GenericAlias`` with **no ``__mro__``**,
    so walking one raises ``AttributeError`` before any of this module's own
    error handling runs (review F1). That defeated the "fail loudly, name the
    offender" guarantee *and* made a correctly-registered generic impossible to
    decode.

    ``list[int]`` hid the bug for the whole first draft, because
    ``types.GenericAlias`` proxies ``__mro__`` to ``list`` while
    ``typing._GenericAlias`` does not — two spellings of "parametrized
    generic", only one of which fails.
    """
    resolved = typing.get_origin(candidate) or candidate
    return resolved if isinstance(resolved, type) else None


def _lookup[C](table: dict[type, C], candidate: object) -> C | None:
    """The registered conversion for ``candidate``, walking its MRO.

    Generic in the conversion type rather than returning a union of the two:
    the encoder takes one argument and the decoder takes two, so a union return
    is ill-typed at *both* call sites. ty caught that — the union typechecked
    the table and lost the arity.

    MRO order rather than dict iteration order, so a registration for a
    subclass wins over one for its base regardless of which was added first —
    insertion order is not a property anyone should have to reason about.
    """
    resolved = _runtime_class(candidate)
    if resolved is None:
        return None
    for base in resolved.__mro__:
        conversion = table.get(base)
        if conversion is not None:
            return conversion
    return None


def enc_hook(obj: object) -> object:
    """Msgspec's encode hook: convert an unsupported instance to a supported one.

    msgspec calls this only for types it cannot encode itself, so reaching here
    is already evidence the type needs a registration.

    Args:
        obj: The instance msgspec could not encode.

    Returns:
        A value msgspec can encode.

    Raises:
        UnsupportedTypeError: No conversion is registered for ``obj``'s type.
    """
    conversion = _lookup(_ENCODERS, type(obj))
    if conversion is None:
        raise UnsupportedTypeError(type(obj), "encode")
    return conversion(obj)


def dec_hook(target: type, obj: object) -> object:
    """Msgspec's decode hook: rebuild an unsupported type from a supported one.

    msgspec passes the **annotation** it is decoding into, which is the type
    written in the model — ``Path``, not the ``PosixPath`` it will construct.
    The conversion is handed that annotation too, so a family of types
    (``PurePosixPath``, ``PureWindowsPath``) needs one registration rather than
    one per flavour.

    Args:
        target: The annotated type to produce.
        obj: The primitive msgspec decoded from the wire.

    Returns:
        An instance of ``target``.

    Raises:
        UnsupportedTypeError: No conversion is registered for ``target``.
    """
    conversion = _lookup(_DECODERS, target)
    if conversion is None:
        raise UnsupportedTypeError(_runtime_class(target) or type(target), "decode")
    return conversion(target, obj)


def encode(obj: object, *, fmt: Format = Format.JSON) -> bytes:
    """Encode ``obj``, applying this project's conversions.

    Args:
        obj: The value to encode.
        fmt: The wire format. Defaults to JSON, the record form #669 chose.

    Returns:
        The encoded bytes.

    Raises:
        UnsupportedTypeError: A value has no registered conversion.
        ValueError: ``fmt`` is not a :class:`Format`.
    """
    match fmt:
        case Format.JSON:
            return msgspec.json.encode(obj, enc_hook=enc_hook)
        case Format.MSGPACK:
            return msgspec.msgpack.encode(obj, enc_hook=enc_hook)
        case _:
            raise ValueError(_unknown_format(fmt))


def decode[T](data: bytes, target: type[T], *, fmt: Format = Format.JSON) -> T:
    """Decode ``data`` into ``target``, applying this project's conversions.

    Args:
        data: The encoded bytes.
        target: The type to decode into — msgspec validates against it.
        fmt: The wire format. Defaults to JSON.

    Returns:
        An instance of ``target``.

    Raises:
        UnsupportedTypeError: ``target`` has no registered conversion.
        ValueError: ``fmt`` is not a :class:`Format`.
        msgspec.ValidationError: ``data`` does not match ``target``.
    """
    match fmt:
        case Format.JSON:
            return msgspec.json.decode(data, type=target, dec_hook=dec_hook)
        case Format.MSGPACK:
            return msgspec.msgpack.decode(data, type=target, dec_hook=dec_hook)
        case _:
            raise ValueError(_unknown_format(fmt))
