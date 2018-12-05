# logmerge

logmerge merges multiple log files into a single stream, preserving the total ordering of events across the multiple log files.

## Features

- Supports multiple timestamp formats
  - Date and time with either fractional seconds or comma-separated milliseconds 
  - Integer or floating point time_t (base-1970)
- Can tag each merged line with an arbitrary text tag per source log
- Can color-code lines per log (using ANSI escape sequences)

## Limitations

- Assumes all timestamps are UTC. The currently-supported timestamp formats don't support a timezone tag.
- Timestamps are not reformatted. If merged logs use different timestamp formats, the merged log will expose that.

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
