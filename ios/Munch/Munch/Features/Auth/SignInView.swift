// The Sign in with Apple gate (spec §8.5). Shown only when Firebase auth is
// active and the user isn't already signed in; the $0 demo skips it entirely
// (DemoAuthProvider is "always signed in"). Returning users are auto-signed-in
// at launch, so this screen appears only on first sign-in or after sign-out.

import AuthenticationServices
import SwiftUI

struct SignInView: View {
    @Environment(AppContainer.self) private var container
    @State private var currentNonce: String?
    @State private var errorMessage: String?
    @State private var working = false

    var body: some View {
        VStack(spacing: Theme.space6) {
            Spacer()
            Text("Munch")
                .font(.munchTitle)
                .foregroundStyle(Theme.accent)
            Text("Stop deciding. Start eating.")
                .font(.title3)
                .foregroundStyle(Theme.inkSecondary)
                .multilineTextAlignment(.center)
            Text("🍜")
                .font(.system(size: 64))
                .accessibilityHidden(true)
            Spacer()

            if working {
                ProgressView()
            } else {
                SignInWithAppleButton(.signIn) { request in
                    let nonce = AppleNonce.make()
                    currentNonce = nonce
                    request.requestedScopes = [.fullName, .email]
                    request.nonce = AppleNonce.sha256(nonce)
                } onCompletion: { result in
                    handle(result)
                }
                .signInWithAppleButtonStyle(.black)
                .frame(height: 54)
                .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
                .accessibilityIdentifier("sign-in-apple")
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.footnote)
                    .foregroundStyle(Theme.nope)
                    .multilineTextAlignment(.center)
            }

            Text("By continuing you agree to our Terms and Privacy Policy.")
                .font(.caption2)
                .foregroundStyle(Theme.inkSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(Theme.space7)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.paper)
        .ignoresSafeArea()
    }

    private func handle(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case let .success(authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let tokenData = credential.identityToken,
                let idToken = String(data: tokenData, encoding: .utf8),
                let nonce = currentNonce
            else {
                errorMessage = "Apple sign-in didn't return a token. Please try again."
                return
            }
            let appleAuthCode = credential.authorizationCode
                .flatMap { String(data: $0, encoding: .utf8) }
            working = true
            errorMessage = nil
            Task {
                await container.completeAppleSignIn(
                    idToken: idToken,
                    rawNonce: nonce,
                    fullName: credential.fullName,
                    appleAuthCode: appleAuthCode
                )
                working = false
                if !container.isSignedIn {
                    errorMessage = "Couldn't complete sign-in. Please try again."
                }
            }
        case let .failure(error):
            // A user-initiated cancel is not an error worth shouting about.
            if (error as? ASAuthorizationError)?.code != .canceled {
                errorMessage = "Couldn't sign in. Please try again."
            }
        }
    }
}
