import Foundation
import JBAXKit

let outcome = run(Array(CommandLine.arguments.dropFirst()))
print(outcome.json)
exit(outcome.code)
