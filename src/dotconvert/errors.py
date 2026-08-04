class DotConvertError(Exception):
    """Base application error suitable for presentation to the user."""


class UnsupportedFormatError(DotConvertError):
    pass


class UnsafeArchiveError(DotConvertError):
    pass


class ExternalToolError(DotConvertError):
    pass


class UserDecisionRequired(DotConvertError):
    pass
