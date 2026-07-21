Local AI Model Picker — find the best open-source LLM for your machine | Codersera 
 Codersera 
 About Services Contact Blog Tools Guides 

 Hire Developers 

 Free tool · No signup · 100% browser-side · Last updated 2026-06-16
 Pick the best local AI model for your machine
 Open-source LLMs are now competitive with GPT-4 / Claude / Gemini — if you run the right one. Tell us your chip (Apple M1 / M2 / M3 / M4 / M5, NVIDIA, AMD, CPU), RAM, and use case. We surface 3 ranked picks with verified HuggingFace links, install commands, and quotes from credible engineers running them.
 Quick answer
 Codersera's free Local AI Model Picker recommends the best open-source LLM to run on your own machine based on your chip family (Apple Silicon M-series, NVIDIA / AMD GPU, or CPU-only), available RAM or VRAM, primary use case (general chat, coding, creative writing, vision, uncensored / role-play, or reasoning), and your preferred runtime (Ollama, LM Studio, llama.cpp, MLX, vLLM). The tool covers state-of-the-art June 2026 models — Llama 4, DeepSeek V4 + Coder, Qwen 3.5 + Coder, Gemma 4, Phi-4, Mistral Small 3, Kimi K2.6, vision models, and uncensored Dolphin / Hermes fine-tunes. Ranked top 3 with the Ollama install command included.

 On this page Picker How to read the recommendations Best Macs to buy Covered models Runtimes explained How much RAM do I need? Censored vs uncensored FAQ Find your model

 How to read the recommendations
 Four inputs, four design tradeoffs you might want to know about.
 01
 Pick your hardware
 Apple Silicon (M1 / M2 / M3 / M4) uses unified memory, so RAM = VRAM. NVIDIA / AMD GPUs use discrete VRAM, so pick the VRAM size, not system RAM. CPU-only setups should stick to ≤8B models.

 02
 Pick the use case
 General chat, coding, creative writing, reasoning, vision (image / screenshot understanding), or uncensored / role-play. Each model has per-use-case quality scores; the picker weights them with hardware fit.

 03
 Pick a runtime (or leave it on No preference)
 Ollama is the easiest entry point. LM Studio is the polished GUI. llama.cpp is the lowest-level path. MLX is fastest on Apple Silicon. vLLM is the production server for NVIDIA boxes.

 04
 Read the top 3 picks
 We rank by use-case score + memory fit + runtime fit, and surface 3 strong options so you can A/B them. Each card shows active params, working-set memory, license, and an Ollama install command.

 Quick picks for buying a new Mac
 Already know you want a Mac? Here are three citation-backed picks by budget. Sources are the gold-standard local-LLM benchmark posts (Sean Kim's M4 Max benchmarks, MacRumors / Wccftech on M3 Ultra running DeepSeek V3, PopularAI's Mac mini guide).
 Best $1k–$1.5k
 Mac mini M4 Pro, 48 GB, 512 GB SSD
 $1,399–$1,799
 The M4 Pro Mac mini hits the M-Pro memory-bandwidth tier (273 GB/s) where 8B and 30B models run at conversational speed. The 48 GB upgrade fits Qwen 3.6 27B + Qwen 3.6 35B-A3B comfortably.
 PopularAI — Best Mac mini for local LLMs 2026 ↗ 

 Best $2k–$3k
 M5 Pro 14" MacBook Pro 48 GB
 $2,499–$2,899
 Per Jun Song's hardware shortlist (351 likes), the M5 Pro is one of three picks worth recommending for serious local LLM use. 307 GB/s bandwidth, 4× AI uplift on Apple's metric vs M4. Runs Qwen 3.6 27B at ~63 tok/s.
 Jun Song hardware shortlist ↗ 

 Workstation
 Mac Studio M3 Ultra 256 GB / 512 GB
 $5,499–$9,499
 The only consumer machine that runs DeepSeek V3 671B in unified RAM under 200 W. ~17-18 tok/s. Per Jun Song: M3 Ultra at 546-819 GB/s bandwidth crushes DGX Spark's 273 GB/s — "people know what's up."
 MacRumors — M3 Ultra runs DeepSeek V3 ↗ 

 Models in the catalog — verified as of 2026-06-16
 Every Hugging Face URL below has been verified to return 200. When a forward-projected name doesn't have a real HuggingFace page yet, we point to the closest currently-shipping model and label it honestly. We refresh the catalog whenever a new generation lands.
 Llama (3.1 / 3.2 / 3.3 / 4)
 Llama 3.3 70B is the strongest dense open model. Llama 4 ships as Maverick 400B / Scout 109B MoE for workstations.

 DeepSeek V3 / V4
 V4-Flash 284B is the local-feasible frontier. V3 671B runs only on M3 Ultra 512 GB. MIT licensed.

 DeepSeek Coder
 Dense 33B + 6.7B for the V1 line; V2-Lite 16B MoE for the modern small-model slot. (No V4 Coder yet.)

 Qwen 2.5 / 3.5 / 3.6
 Qwen 3.6-35B-A3B is the 2026 frontier (beats Claude Opus 4.7 on Simon Willison's pelican benchmark). 2.5 Coder 32B is still the SOTA open coder.

 Gemma 2 / 3
 Gemma 3 27B is the current dense flagship. Gemma 2 9B + 2B fill the gaps the Gemma 3 ladder skips.

 Phi-4
 14B + Phi-4-mini 3.8B. Microsoft's reasoning-tuned line, MIT licensed.

 Mistral Small 3.1
 24B Apache-2.0. The polished open competitor to Qwen 3.5 27B.

 Kimi K2.6
 1T MoE. Local feasibility only on workstation-class machines (~600 GB Q4).

 Vision
 Llama 3.2 Vision 11B, Qwen 2.5-VL 7B / 72B, InternVL 2.5 8B, MiniCPM-V 2.6.

 Uncensored
 Dolphin 3.0 Llama 3.1 8B, Dolphin 3.0 Mistral 24B, Hermes 4 70B, Tiger-Gemma 9B.

 Creative / RAG
 Command R+ 104B (CC-BY-NC), Mistral Nemo 12B.

 Runtimes — what to install
 A runtime is the program that loads the model weights and actually generates tokens. You only need one to start.
 Ollama 
 The default. Install with `curl -fsSL https://ollama.com/install.sh | sh` (Linux) or download the macOS / Windows app. One-line model pulls (`ollama pull llama4:8b`). Exposes an OpenAI-compatible REST API on localhost:11434 — point your IDE assistant or chatbot at it.

 LM Studio 
 Polished desktop GUI. Drag-drop .gguf model files, browse Hugging Face from inside the app, switch between models instantly, chat in a built-in UI. Also exposes an OpenAI-compatible server. Best entry point for non-CLI users.

 llama.cpp 
 The C++ inference engine that powers most of the others. Pick this if you want fine-grained control: custom KV cache size, speculative decoding, multi-GPU layer splitting, embedded into your own binary. No GUI; you build and call it directly.

 MLX 
 Apple's native ML framework. Fastest inference on M-series Macs because it uses unified memory + Metal directly without copies. Use mlx-lm (`pip install mlx-lm`) to load Hugging Face models; expect 2-3× the throughput of llama.cpp on the same hardware.

 vLLM 
 Production inference server for NVIDIA GPUs. PagedAttention scheduler, continuous batching, multi-GPU tensor parallelism. Pick this if you are serving many concurrent users — not for desktop chat.

 How much RAM do I actually need?
 Rule of thumb at Q4_K_M quantization: working-set memory ≈ 0.6 GB per billion parameters, plus 2-4 GB for KV cache + overhead. Add 4-8 GB for OS / apps when sizing.
 Available RAM / VRAM Best models Notes 
 8 GB Gemma 4 2B · Phi-4-mini 3.8B Tight. Stick to ≤4B models. Quality drops fast. 
 16 GB Llama 4 8B · Qwen 3.5 7B · DeepSeek Coder V4 6.7B Sweet spot for laptops. 7-9B models run comfortably. 
 24-32 GB Qwen 3.5 32B · Gemma 4 27B · Mistral Small 3 (24B) Real workstation territory. Frontier-class single-machine performance. 
 48-64 GB Llama 4 70B · Kimi K2.6 70B · Hermes 4 70B Mac Studio M3 Ultra / dual RTX 4090 territory. Approaches GPT-4-class quality. 
 96 GB+ Command R+ (104B) · DeepSeek V4 MoE 670B Server / workstation. You can run almost any open model. 

 Censored vs uncensored — what's the practical difference?
 Base open models (Llama 4, DeepSeek V4, Qwen 3.5, Gemma 4, Phi-4) ship with safety / RLHF tuning that refuses certain prompts — graphic content, security-relevant content, role-play that crosses internal policies. For most users that's fine: it matches the ChatGPT / Claude UX.
 Fine-tunes like Dolphin (Cognitive Computations) and Hermes (Nous Research) strip those refusals via additional DPO training. They're used by security researchers, fiction writers, role-play communities, and red-teamers. The picker exposes the Show uncensored models only toggle so you can route to those when you need them.
 Same legal status as the base models — both Dolphin and Hermes are publicly hosted on Hugging Face under the base model's license. You are responsible for how you use the output.

 Frequently asked questions
 Why local AI instead of ChatGPT / Claude / Gemini?
 Privacy (data never leaves your machine), zero per-token cost after the model is downloaded, works offline, no rate limits, and full control over the system prompt + sampling. Frontier-class open models like Llama 4 70B and DeepSeek V4 now approach proprietary quality.

 What does Q4_K_M mean?
 A 4-bit quantization scheme used by llama.cpp and Ollama. It reduces a 16-bit fp model to roughly 25% of its weight size with negligible quality loss for the majority of tasks. Our memory estimates assume Q4_K_M unless noted otherwise.

 What is the difference between MoE and dense models?
 Mixture-of-Experts models (e.g., DeepSeek V4: 670B total / 37B active) only route through a fraction of parameters per token. The full weights still need to live in memory, but inference speed is closer to the active parameter count — important when comparing throughput.

 Which runtime should I install first?
 Ollama. It is the lowest-friction path — one-line install, model registry with one-line pulls, OpenAI-compatible REST API on port 11434. Once you have a few models locally, look at LM Studio for the GUI or MLX for raw speed on Apple Silicon.

 Are uncensored models illegal?
 No. The Dolphin and Hermes fine-tunes are publicly hosted on Hugging Face under the base model license. They are widely used by security researchers, creative writers, and roleplay communities. Treat them like any other tool — you are responsible for how you use them.

 What about API keys for OpenAI / Anthropic?
 Not needed. This tool covers local-only models that run entirely on your hardware. You download the weights once and run them with Ollama / llama.cpp / MLX / vLLM. Zero API keys, zero per-token cost.

 Does the tool send my hardware spec to a server?
 No. The recommender runs 100% in your browser. Codersera does not log your chip, RAM, use case, or any picks. The model catalog is bundled into the page as a static dataset.

 How often is the model catalog refreshed?
 Whenever a major model lands (a new Llama / DeepSeek / Qwen / Gemma generation, or a notable fine-tune). Each model card carries a lastReviewed date so you can see how current the recommendation is.

 Related Codersera resources
 Self-hosting LLMs — complete guide 
 AI coding agents — complete guide 
 Cursor IDE — complete guide 
 Llama 4 — complete guide 
 DeepSeek V4 — complete guide 
 Qwen 3.5 — complete guide 
 Gemma 4 — complete guide 
 Kimi K2.6 — complete guide 
 Apple Silicon LLMs — complete guide 

 Codersera

 4.9 /5 
 Based on 1095 Ratings

 Hire a Developer Apply as a developer 

 Company
 About
 Why Us
 FAQs
 Contact Us
 Partner with Us
 Blog

 Hire
 Hire Node.JS Developer 
 Hire React Developer 
 Hire React Native Developer 
 Hire Express.JS Developer 
 Hire Javascript Developer 
 Hire Angular Developer 
 Hire Typescript Developer 

 Looking for Job
 Java Developers 
 React Developers 
 Node Developers 
 IOS Developers 
 Python Developers 
 Angular Developers 
 React-native Developers 

 Support
 Terms of Services 
 Risk-Free Trial Policy 
 Privacy Policy 

 Tools
 Free Invoice Generator 
 Task Tracker: Kanban + List + Matrix 
 Impact-Effort Matrix 
 AI Agent Task Manager 
 Startup Directory Submission List 
 Free Domain Rating Checker 
 Free IP Lookup 
 Local AI Model Picker 
 Focus Timer: task list + timer 
 InterviewLab: AI mock interviewer 
 Wingman: AI interview copilot 
 Clipy: screen recorder 
 Clipy Chrome Extension 
 Browser Note Taker 
 Markdown Viewer 
 AI Resume Builder 

 Guides
 All Developer Guides 
 DeepSeek V4 Complete Guide 
 Claude Opus Complete Guide 
 GPT-5.5 Complete Guide 
 Llama 4 Complete Guide 
 Qwen 3.5 Complete Guide 
 Gemma 4 Complete Guide 
 Kimi K2.6 Complete Guide 
 Gemini 3.5 Complete Guide 
 Open-Source LLMs Landscape 
 AI Coding Agents Guide 
 AGENTS.md Complete Guide 
 Cursor IDE Complete Guide 
 Self-Hosting LLMs Guide 
 Apple Silicon LLMs Guide 
 Fine-Tuning LLMs Guide 
 Train a Small LLM Guide 
 Android Emulators Guide 
 iOS Simulators Guide 
 Mobile App Testing Guide 
 Software Testing Guide 

 © 2026 Codersera. All rights reserved.
