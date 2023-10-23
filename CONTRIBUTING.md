# Introduction

We welcome community contributions to this library and we hope that together we can expand the coverage of ASM ready data for everyone.

In order to contribute you will need to have an Individual or Corporate Contributor License Agreement (CLA) on file with Benchling depending on if you are contributing on your own time or as part of another company. When you make your first pull request we will check if you have a CLA and if not take care of that with you first. The process is quick and painless and helps us to make sure that you and everyone who uses your code in the future is protected.

## GPG keys and signed commits
All commits to this repository must be signed. To set up commit signatures, please do the following:
- Check for [existing GPG keys](https://docs.github.com/en/authentication/managing-commit-signature-verification/checking-for-existing-gpg-keys).
- Otherwise, [generate a new GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key).
  - On macOS, GPG can be installed by running `brew install gpg`.
- [Add your GPG key to GitHub](https://docs.github.com/en/authentication/managing-commit-signature-verification/adding-a-gpg-key-to-your-github-account).
- [Tell Git about your signing key](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key).
  - Follow up until step 5.

To configure commits to be signed by default within this repo, run `git config commit.gpgsign true`.

# Adding a new converter

Determine if the ASM schemas you need are in [the schema folder](../src/allotropy/allotrope/schemas). We keep a copy of published ASM schemas here as well as our proposed changes that are yet to be taken up by the Allotrope Foundation. We expect this to be eventually consistent with the public ASM schemas.

## If the ASM schema you need is available

In this case we already have some code in the library to handle instruments of this type and you should look at those for examples of how to structure your own code. Each converter consists of two main pieces:
1. A `Parser` class -- this implements [`VendorParser`](src/allotropy/parsers/vendor_parser.py) and does most of the work converting the instrument data to ASM.
2. Either:
  - A `Structure` file that the `Parser` uses to build an in memory representation of the instrument data that can be serialized to ASM.
  - A `Reader` file that the `Parser` uses to read directly from the file, if accessing the file data does not require much logic.

## If the ASM schema you need is not available

Please open an issue and talk to us about adding it. There is a bit more work involved in this case but we would still love to work with you to get the instrument type that you desire into the library!


# Other issues

Please open an issue for other concerns or issues you want to communicate to us. In the case of a security vulnerability please follow the [Github provided guidance](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
