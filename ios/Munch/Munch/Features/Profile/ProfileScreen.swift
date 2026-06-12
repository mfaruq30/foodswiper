// The Profile tab: taste summary, dietary filters, legal/attribution links,
// and the in-app account-deletion path (D-013). Apple 5.1.1(v) requires
// deletion to be reachable inside the app — this screen is that path.

import MunchKit
import SwiftUI

struct ProfileScreen: View {
    @Environment(AppContainer.self) private var container
    @State private var viewModel = ProfileViewModel()
    @State private var confirmingDelete = false

    /// The four launch dietary filters; `flag` values are the server ids.
    private static let dietaryOptions: [DietaryOption] = [
        DietaryOption(flag: "vegetarian", label: "Vegetarian"),
        DietaryOption(flag: "vegan", label: "Vegan"),
        DietaryOption(flag: "gluten_free", label: "Gluten-free"),
        DietaryOption(flag: "halal", label: "Halal"),
    ]

    /// Honest footer: dietary coverage in open data is patchy, and an empty
    /// deck should point users at the fix, not leave them guessing.
    // swiftformat:disable indent -- string interiors are content, not code
    private static let dietaryFooter = """
        Filters every deck. Coverage comes from OpenStreetMap tags and can be \
        sparse — if decks come up empty, try relaxing these.
        """
    // swiftformat:enable indent

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Profile")
                .background(Theme.paper)
        }
        .task { await viewModel.load(container: container) }
    }

    // MARK: - Screen states

    @ViewBuilder
    private var content: some View {
        if let profile = viewModel.profile {
            profileList(profile)
        } else if let message = viewModel.errorMessage {
            StateMessage(
                icon: "person.crop.circle.badge.exclamationmark",
                title: "Couldn't load your profile",
                detail: message,
                retryTitle: "Try again",
                retry: { Task { await viewModel.load(container: container) } }
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            // Covers both in-flight loads and the first frame before .task fires.
            ProgressView("Loading your profile…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Loaded list

    private func profileList(_ profile: ProfileBody) -> some View {
        List {
            tasteSection(profile)
            dietarySection(profile)
            aboutSection
            accountSection
            footnoteSection
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(Theme.paper)
        .alert("Something went wrong", isPresented: saveErrorShown) {
            Button("OK", role: .cancel) { viewModel.errorMessage = nil }
        } message: {
            Text(viewModel.errorMessage ?? "Please try again.")
        }
        .confirmationDialog(
            "This permanently deletes your profile and swipe history.",
            isPresented: $confirmingDelete,
            titleVisibility: .visible
        ) {
            Button("Delete everything", role: .destructive) {
                Task { _ = await viewModel.deleteAccount(container: container) }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    /// Save/delete failures surface as an alert while the list stays on
    /// screen; the full StateMessage is reserved for load failures.
    private var saveErrorShown: Binding<Bool> {
        Binding(
            get: { viewModel.profile != nil && viewModel.errorMessage != nil },
            set: { shown in
                if !shown { viewModel.errorMessage = nil }
            }
        )
    }

    // MARK: - Sections

    private func tasteSection(_ profile: ProfileBody) -> some View {
        Section("Your taste") {
            if profile.anchorCuisines.isEmpty {
                Text("Pick favorites during onboarding")
                    .font(.body)
                    .foregroundStyle(Theme.inkSecondary)
            } else {
                FlowRow(spacing: Theme.space3) {
                    ForEach(profile.anchorCuisines, id: \.self) { cuisineID in
                        cuisineChip(cuisineID)
                    }
                }
                .padding(.vertical, Theme.space2)
            }
        }
        .listRowBackground(Theme.surface)
    }

    /// Non-interactive cuisine chip — anchors are chosen in onboarding, not
    /// edited here, so these read as a summary rather than controls.
    private func cuisineChip(_ cuisineID: String) -> some View {
        let display = CuisineCatalog.display(for: cuisineID)
        return Text("\(display.emoji) \(display.name)")
            .font(.subheadline.weight(.medium))
            .padding(.horizontal, Theme.space4)
            .padding(.vertical, Theme.space3)
            .background(Theme.accentSoft)
            .foregroundStyle(Theme.accent)
            .clipShape(Capsule())
            .accessibilityLabel(display.name)
    }

    private func dietarySection(_ profile: ProfileBody) -> some View {
        Section {
            FlowRow(spacing: Theme.space3) {
                ForEach(Self.dietaryOptions) { option in
                    SelectableChip(
                        label: option.label,
                        emoji: nil,
                        selected: profile.dietaryFlags.contains(option.flag),
                        action: {
                            Task {
                                await viewModel.toggleDietary(option.flag, container: container)
                            }
                        }
                    )
                }
            }
            .padding(.vertical, Theme.space2)
        } header: {
            Text("Dietary")
        } footer: {
            Text(Self.dietaryFooter)
        }
        .listRowBackground(Theme.surface)
    }

    private var aboutSection: some View {
        Section("About") {
            NavigationLink("Privacy Policy") { LegalView(document: .privacy) }
            NavigationLink("Terms of Service") { LegalView(document: .terms) }
            NavigationLink("Data sources & attribution") { DataSourcesView() }
        }
        .listRowBackground(Theme.surface)
    }

    private var accountSection: some View {
        Section("Account") {
            HStack {
                Text("Home metro")
                    .foregroundStyle(Theme.ink)
                Spacer()
                Text(metroLabel)
                    .foregroundStyle(Theme.inkSecondary)
            }
            .frame(minHeight: 44)
            .accessibilityElement(children: .combine)

            if viewModel.deleting {
                HStack(spacing: Theme.space4) {
                    ProgressView()
                    Text("Deleting your account…")
                        .foregroundStyle(Theme.inkSecondary)
                }
                .frame(minHeight: 44)
            } else {
                Button(role: .destructive) {
                    confirmingDelete = true
                } label: {
                    Text("Delete my account")
                        .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                }
                .foregroundStyle(Theme.nope)
                .accessibilityHint("Permanently deletes your profile and swipe history")
            }
        }
        .listRowBackground(Theme.surface)
    }

    /// Demo provenance footnote — ODbL credit stays one tap away from every
    /// screen that shows restaurant data, so it links to the credits page.
    private var footnoteSection: some View {
        Section {
            NavigationLink {
                DataSourcesView()
            } label: {
                Text("Munch demo • data © OpenStreetMap contributors")
                    .font(.caption)
                    .foregroundStyle(Theme.inkSecondary)
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .center)
            }
            .listRowBackground(Color.clear)
        }
    }

    /// Display name for the persisted metro id ("nyc" → "New York City").
    private var metroLabel: String {
        guard let raw = container.homeMetro else { return "Not set" }
        return Metro(rawValue: raw)?.displayName ?? raw
    }
}

// MARK: - Supporting types

/// A dietary filter the UI can toggle; `flag` is the server's snake_case id.
private struct DietaryOption: Identifiable {
    let flag: String
    let label: String
    var id: String {
        flag
    }
}

/// Minimal wrapping chip row — SwiftUI has no built-in flow layout, and chips
/// of varying width must wrap instead of truncate (Dynamic Type especially).
private struct FlowRow: Layout {
    var spacing: CGFloat = Theme.space3

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache _: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalWidth: CGFloat = 0
        var totalHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if rowWidth > 0, rowWidth + spacing + size.width > maxWidth {
                totalWidth = max(totalWidth, rowWidth)
                totalHeight += rowHeight + spacing
                rowWidth = 0
                rowHeight = 0
            }
            rowWidth += (rowWidth > 0 ? spacing : 0) + size.width
            rowHeight = max(rowHeight, size.height)
        }
        totalWidth = max(totalWidth, rowWidth)
        totalHeight += rowHeight
        return CGSize(width: maxWidth.isFinite ? maxWidth : totalWidth, height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal _: ProposedViewSize, subviews: Subviews, cache _: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > bounds.minX, x + spacing + size.width > bounds.maxX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            if x > bounds.minX {
                x += spacing
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: .unspecified)
            x += size.width
            rowHeight = max(rowHeight, size.height)
        }
    }
}
