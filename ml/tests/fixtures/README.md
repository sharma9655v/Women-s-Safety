# TEST FIXTURES — NOT REAL DATA
#
# Everything in this directory is synthetic fixture material used ONLY to unit-
# test the dataset pipeline mechanics (parsing, normalization, deduplication,
# privacy generalization, export). These rows describe no real incidents, no
# real people, and no real locations.
#
# These files are NEVER inputs to ML training. The build pipeline only ingests
# sources listed and enabled in ml/ml/data/config/sources.yaml — this fixtures
# directory is not referenced there.

fixture_records.csv: 6 synthetic CSV rows exercising date formats,
    category variants, missing coordinates, and duplicate source record IDs.
