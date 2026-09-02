# Domain Rules Agent Rules

- Write tests first for every boundary and rounding edge.
- Use integer/rational math exactly as game-design docs specify; no gameplay floats.
- Do not clamp corrupt input unless the rule explicitly describes an effect clamp.
- Do not read config, clocks, globals, RNG, files, or model output.
- Assert inputs remain unchanged on success and failure.
