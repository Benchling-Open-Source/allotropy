# allotropy Project Governance

The allotropy project uses a governance model commonly described as
Benevolent Dictator For Life ([BDFL][wikipedia-bdfl]). This document
outlines our implementation of this model.  The process for
contributing is described in a separate document called
[CONTRIBUTING.md](./CONTRIBUTING.md).

## Terms

*   user: anyone who interacts with the project.

*   contributor: anyone who has contributed to the project in any way
    and to any degree. Contributions may include code, documentation,
    reviews, manual testing, etc. All contributors are listed in
    `pyproject.toml`.

*   core contributor: anyone who has contributed repeatedly and
    significantly to the project.  Core contributors are recognized by
    GitHub "Member" badges.

*   Benevolent Dictator For Life (BDFL): the person who makes decisions
    when consensus cannot be reached. The project's current BDFL is
    [Nathan Stender][stender-nathan].

## Decision Making Process

Contributors try to reach consensus via discussion. When consensus
cannot be reached in a reasonable time, the BDFL takes the following
steps:

1.  Creates an issue in the project's [GitHub repository][repo]
    labeled `governance` with a suitable title.

2.  Waits at least 48 hours for contributors to add comments to the
    issue.

3.  Adds a comment with the final decision and closes the issue.

## Changing Governance

1.  The BDFL may choose a replacement at any point and cede authority
    to them. If this happens, the decision must be announced and
    recorded in the manner described above for decisions in the
    absence of consensus.

    1.  The new BDFL must clearly state that they accept their new
        responsibilities.

    2.  The time at which the new BDFL assumes their responsibilities
        must be clearly stated.

2.  The BDFL may alternatively decide to move to a Steering Committee
    governance model, in which case this document must be replaced with
    a new description of roles and responsibilities.

[repo]: https://github.com/Benchling-Open-Source/allotropy
[stender-nathan]: https://github.com/nathan-stender
[wikipedia-bdfl]: https://en.wikipedia.org/wiki/Benevolent_dictator_for_life
