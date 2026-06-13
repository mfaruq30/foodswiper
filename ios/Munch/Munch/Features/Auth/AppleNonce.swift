// Sign in with Apple nonce — replay protection (Apple + Firebase both require
// it). The flow: send sha256(nonce) to Apple; Apple echoes it inside the signed
// identity token; Firebase re-hashes the RAW nonce we kept and checks the match.
// A mismatch means the token was intercepted/replayed.
//
// CryptoKit is a system framework, so this compiles and is used in every build.

import CryptoKit
import Foundation

enum AppleNonce {
    /// A cryptographically random nonce string (the RAW value Firebase needs).
    static func make(length: Int = 32) -> String {
        let charset: [Character] =
            Array("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-._")
        var result = ""
        var remaining = length
        while remaining > 0 {
            var random: UInt8 = 0
            let status = SecRandomCopyBytes(kSecRandomDefault, 1, &random)
            // SecRandom failure is effectively impossible; if it ever did, fail
            // closed by retrying rather than emitting a predictable nonce.
            guard status == errSecSuccess else { continue }
            if random < charset.count {
                result.append(charset[Int(random)])
                remaining -= 1
            }
        }
        return result
    }

    /// SHA-256 hex digest — the value handed to Apple's authorization request.
    static func sha256(_ input: String) -> String {
        let digest = SHA256.hash(data: Data(input.utf8))
        return digest.map { String(format: "%02x", $0) }.joined()
    }
}
