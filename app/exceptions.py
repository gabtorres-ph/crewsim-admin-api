class ResourceNotFoundError(Exception):
    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' was not found")


class ResourceConflictError(Exception):
    pass


class InvalidOperationError(Exception):
    pass
