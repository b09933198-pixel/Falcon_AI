# ADR-013

## Feature First Architecture

### Decision

Every market signal inside Falcon_AI must first become a Feature before entering any AI, Probability, or Decision engine.

Indicators are never consumed directly by higher layers.

Pipeline → FeatureVector → AI