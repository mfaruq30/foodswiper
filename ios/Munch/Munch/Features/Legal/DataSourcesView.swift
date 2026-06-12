// ODbL attribution screen — license compliance, not decoration: using
// OpenStreetMap data requires visible credit plus a link to the license.
// NYC Open Data and Analyze Boston credits ride along, and the closing line
// states honestly where match percentages come from (Munch users — scores
// are never scraped third-party ratings, per ALGORITHM.md).

import SwiftUI

struct DataSourcesView: View {
    /// ODbL requires a working link to the OSM copyright page; the literal is
    /// constant and known-valid, so the force unwrap cannot fail at runtime.
    private static let osmCopyright = URL(string: "https://www.openstreetmap.org/copyright")!

    // swiftformat:disable indent -- string interiors are content, not code
    private static let osmDetail = """
        Restaurant names, locations, cuisines, and dietary tags come from \
        OpenStreetMap, used under the Open Database License (ODbL).
        """

    private static let nycDetail = """
        New York restaurant inspection records come from the NYC Department of \
        Health and Mental Hygiene, published on NYC Open Data.
        """

    private static let bostonDetail = """
        Boston food establishment licenses come from Analyze Boston, published \
        under the Public Domain Dedication and License (PDDL).
        """
    // swiftformat:enable indent

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.space6) {
                Text("Data sources")
                    .font(.munchHeading)
                    .foregroundStyle(Theme.ink)

                osmBlock

                sourceBlock(
                    heading: "NYC Open Data — DOHMH inspections",
                    detail: Self.nycDetail
                )

                sourceBlock(
                    heading: "Analyze Boston — food establishment licenses (PDDL)",
                    detail: Self.bostonDetail
                )

                honestyNote
            }
            .padding(Theme.space6)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.paper)
        .navigationTitle("Data sources")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Blocks

    /// The OSM block carries the required copyright line AND license link.
    private var osmBlock: some View {
        VStack(alignment: .leading, spacing: Theme.space3) {
            Text("© OpenStreetMap contributors")
                .font(.headline)
                .foregroundStyle(Theme.ink)
            Text(Self.osmDetail)
                .font(.body)
                .foregroundStyle(Theme.ink)
            Link("openstreetmap.org/copyright", destination: Self.osmCopyright)
                .font(.body.weight(.medium))
                .frame(minHeight: 44, alignment: .leading)
                .accessibilityLabel("Open the OpenStreetMap copyright page")
        }
    }

    /// One credited source: heading + plain-English description.
    private func sourceBlock(heading: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: Theme.space3) {
            Text(heading)
                .font(.headline)
                .foregroundStyle(Theme.ink)
            Text(detail)
                .font(.body)
                .foregroundStyle(Theme.ink)
        }
    }

    /// Provenance honesty: ratings are never scraped, so say so in-app.
    private var honestyNote: some View {
        Text("Munch's match percentages come from Munch users, never scraped ratings.")
            .font(.body.weight(.medium))
            .foregroundStyle(Theme.ink)
            .padding(Theme.space4)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.accentSoft)
            .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
    }
}
