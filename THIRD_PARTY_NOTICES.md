# Third-party notices

## Code copied from OotrR (MIT)

The files in `ootr_tracker/moz/` (and `tools/icon_extract.py`, and the Archipelago connection helpers and the process
memory reader in `ootr_tracker/console/`) are copied or adapted from [Mozencaz/OotrR](https://github.com/Mozencaz/OotrR), v0.8.0
(commit eb66827). Each such file says which file of OotrR it comes from. OotrR's licence:

```
MIT License

Copyright (c) 2026 Mozencaz

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## The module (GPL-3.0-or-later)

`module/` and the prebuilt `ootr_tracker/resources/subsdk7` are GPL-3.0-or-later (`module/LICENSE`), built from
[sloperinaGZ](https://github.com/PracticeROM/sloperina) (PracticeROM, itself based on gz by glankk) and
[ocarinaMIDI](https://github.com/waze3174/ocarinaMIDI) code. Its provenance is listed in `module/README.md` ("Licence and
credits") and in the header of each adapted file. `module/src/third_party` holds stb_truetype (public domain) and zstd's
educational decoder (BSD or GPLv2, Meta Platforms).

## Community check names

`ootr_tracker/resources/check_name_overrides.json` was made from the community's naming spreadsheet ("Token and Check
naming"), whose authors are the people who renamed the checks there. It may change as the spreadsheet does.
