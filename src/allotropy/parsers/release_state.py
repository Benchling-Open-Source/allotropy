from enum import Enum


class ReleaseState(Enum):
    # Ready for production use
    RECOMMENDED = "RECOMMENDED"
    # Working for some cases, may have bugs or need more test cases for hardening
    CANDIDATE_RELEASE = "CANDIDATE_RELEASE"
    # In development, not recommended for production use
    WORKING_DRAFT = "WORKING_DRAFT"
