# Introduction

We welcome community contributions to this library and we hope that together we can expand the coverage of ASM-ready data for everyone.

In order to contribute you will need to have an Individual or Corporate Contributor License Agreement (CLA) on file with Benchling depending on if you are contributing on your own time or as part of another company. You can email opensource@benchling.com to get this process started, or if you do not have a CLA on file when you open your first pull request, Benchling will reach out!

Allotropy follows a [fork and pull model](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/getting-started/about-collaborative-development-models#fork-and-pull-model). To start, fork a copy of the Allotropy repository in GitHub onto your own account and then create your local repository of the fork.

## Contribution conventions

### PR title
The PR title must have a form (`<prefix>: <description>`) and must have one of the following prefixes.

Some prefixes cause the PR title to be included in CHANGELOG generation for a release.

If the prefix is included in the CHANGELOG, the description should have a `<scope> -` prefix (`<prefix>: <scope> - <description>`), e.g.:

`feat: Molecular Devices SoftMax Pro - report non numeric values in error document`

#### Prefix

CHANGELOG prefixes:
* `feat`: A new feature - `Added` section of CHANGELOG
* `fix`: A bug fix - `Fixed` section of CHANGELOG
* `refactor`: Major refactor-only changes (e.g. moving code, reorganizing classes) - `Changed` section of CHANGELOG
* `deprecate`: Deprecate a feature - `Deprecated` section of CHANGELOG
* `remove`: Remove a feature - `Removed` section of CHANGELOG
* `security`: A security related fix - `Security` section of CHANGELOG

other prefixes:
* `release`: Used only for updating the package version for a new release
* `docs`: Documentation only changes
* `style`: Stylistic only changes (e.g. whitespace, formatting)
* `perf`: Performance only changes
* `test`: A change that only introduces new tests or test data
* `chore`: A change to internal systems (e.g. build, ci, dependencies) that does not affect tests

Rules of thumb:
* Changes that affect existing test cases or add new parser tests should almost certainly have a `feat` or `fix` prefix.
* Changes that add a new parser should use the `feat` prefix, (e.g. `feat: ThermoSkanIt - initial implementation`).
* Major refactors that are likely to affect other developers should have a `refactor` prefix, small refactors can use `chore`.
* Removal of functionality must first be deprecated in a PR with the `deprecate` prefix.
* Deprecated functionality can then be removed in the next major version with the `remove` prefix.

#### Scope

If the change should be included in the CHANGELOG, the description should be prefixed with a scope that
makes it clear which parsers are affected by the change.

The scope should be capitalized and end with a dash. The value of the scope prefix depends on how much of the codebase the change affects:

* `Single parser`: Changes that only affects one parser. The scope should be the `DISPLAY_NAME` of that parser (e.g. `Molecular Devices SoftMax Pro -`).
* `Instrument category`: Change that affect all parsers of one instrument category (e.g. changing an ASM schema). The scope should be the `title case` name of that category (e.g. `Plate Reader` for `plate-reader` schemas - see `SUPPORTED_INSTRUMENT_SOFTWARE.adoc` for all categories).
* `Global`: Changes that affect all parsers (e.g. a change that modifies a utility used by all parsers, or the ASM export behavior).
* `Internal`: Change that does not change parser behavior, but is still significant enough to include in CHANGELOG (e.g. major dev utility improvements).

## CHANGELOG
The CHANGELOG will be automatically generated from PR titles with the title prefixes detailed above.

When writing a PR title that will be in the CHANGELOG, it is important to use a title that will make a good CHANGELOG entry.

See: https://docs.gitlab.com/ee/development/changelog.html#writing-good-changelog-entries

In short: "A good changelog entry should be descriptive and concise. It should explain the change to a reader who has zero context about the change. If you have trouble making it both concise and descriptive, err on the side of descriptive."

## Testing
Every PR is run against all lint checks and tests before merging in git.
Be sure to run `hatch run lint` and `hatch run test` before creating a PR to ensure your branch will pass checks.

## GPG keys and signed commits
All commits to this repository must be signed. To set up commit signatures, please do the following:
- Check for [existing GPG keys](https://docs.github.com/en/authentication/managing-commit-signature-verification/checking-for-existing-gpg-keys).
- Otherwise, [generate a new GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key).
  - On macOS, GPG can be installed by running `brew install gpg`.
- [Add your GPG key to GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/adding-a-gpg-key-to-your-github-account).
- [Tell Git about your signing key](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key).
  - Follow up until step 5.

To configure commits to be signed by default within this repo, run this line:
```sh
git config commit.gpgsign true
``````

If you have a passphrase on your GPG key, be sure to add this line to your `~/.zshrc` or `~/.bashrc` (or your respective shell configuration file):

```sh
export GPG_TTY=$(tty)
```

> [!NOTE]
> If you are having trouble signing your commits, when adding commits, make sure to `exit` any `hatch shell` you may have open. Developers have reported issues trying to do so, as commit signing does not work properly in a virtual environment.


# Adding a new converter

Determine if the ASM schemas you need are in [the schema folder](src/allotropy/allotrope/schemas). We keep a copy of published ASM schemas here as well as our proposed changes that are yet to be taken up by the Allotrope Foundation. We expect this to be eventually consistent with the public ASM schemas.

## If the ASM schema you need is available

In this case we already have some code in the library to handle instruments of this type and you should look at those for examples of how to structure your own code. Each converter consists of four main pieces:
1. A `SchemaMapper` -- this defines a set of dataclasses for the parser to populate, and handles populating the ASM schema. This class is defined per schema, so it may already exist, though you may need to add to it if your parser adds a case not yet handled for the schema.
2. A `Reader` class -- this reads the raw contents of the file, which is passed to the `Structure` classes.
3. A `Structure` file -- this defines functions that the `Parser` uses populate the `SchemaMapper` dataclasses. It may construct intermediate dataclasses to organize the raw data of the file, which are then used to populate the `SchemaMapper` dataclasses.
4. A `Parser` class -- this implements [`VendorParser`](src/allotropy/parsers/vendor_parser.py) and is responsible using the `Reader` and `Structure` to create data for the `SchemaMapper`

Run `hatch run scripts:create-parser NAME SCHEMA_REGEX` to create a set of starter files. Where `SCHEMA_REGEX` is a search pattern over schema paths to specify a schema to use.

See our [tutorial](docs/tutorial.md) for a deeper dive on contributing to the `allotropy` library!

## If the ASM schema you need is not available

Please open an issue and talk to us about adding it. There is a bit more work involved in this case but we would still love to work with you to get the instrument type that you desire into the library!

## README
The README contains a list of all available parsers, organized by release state. When adding a new parser,
it must be included in the README. This can be done automatically via:

```sh
hatch run scripts:update-readme
```

# Error messaging

We ask that all error messages thrown in exceptions are written to be clear and useful to developers and end users. As such, please follow these guidelines. `AllotropeConversionError` and helper functions can be found in [`exceptions.py`](src/allotropy/exceptions.py) (and as always, we welcome any additions you may have).
- Catch and raise all errors caused by bad input in this repo as `AllotropeConversionError`.
- Write all messages with proper capitalization and full punctuation.
- As much as possible, include the exact text of the problematic line(s) or value(s) (in single quotes as needed, to add clarity).
- As much as possible, explain why that text was problematic, or what the expected behavior would have been.
- Construct messages using f-strings, when applicable.

## Specific situations
- If a value is not a member of an expected set of values (e.g. an Enum), the text should read: `Unrecognized {key}: '{value}'. Only {valid_values} are supported.` (there is a helper function in [`exceptions.py`](src/allotropy/exceptions.py) for this)
- If an expected value is not present, begin the text with `"Unable to find..."` or `"Unable to determine..."`
- If a certain number of values are expected, begin the text with `"Expected exactly..."`
- If a certain framework is unsupported, begin with the text `"Unsupported..."`


# Other issues

Please open an issue for other concerns or issues you want to communicate to us. In the case of a security vulnerability please follow the [Github provided guidance](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
