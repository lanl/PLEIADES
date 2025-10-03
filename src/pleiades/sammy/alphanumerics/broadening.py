from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting and ending with --------------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Broadening options:
        Is broadening wanted
        broadening_options = [
        ----------------------------
        *   "BROADENING IS WANTED",
            "BROADENING IS NOT WAnted"
        ----------------------------
        ]

"""


class BroadeningOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    broadening_is_wanted: bool = Field(default=True, description="BROADENING IS WANTED")
    broadening_is_not_wanted: bool = Field(default=False, description="BROADENING IS NOT WANTED")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [["broadening_is_wanted", "broadening_is_not_wanted"]]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "BroadeningOptions":
        for group in self.mutually_exclusive_groups:
            true_fields = [f for f in group if getattr(self, f)]
            if not true_fields:
                continue

            user_true = [f for f in true_fields if f in self.model_fields_set]
            default_true = [f for f in true_fields if f not in self.model_fields_set]

            # If >1 user-specified in same group => error
            if len(user_true) > 1:
                raise ValueError(
                    f"Multiple user-specified fields {user_true} are True in group {group}. Only one allowed."
                )

            # If exactly 1 user-specified => turn off all defaults in that group
            if len(user_true) == 1:
                for f in default_true:
                    setattr(self, f, False)
                continue

            # If all True fields are defaults, and more than 1 => error
            if len(default_true) > 1:
                raise ValueError(f"Multiple default fields {default_true} are True in group {group}. Only one allowed.")
        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.broadening_is_wanted:
            commands.append("BROADENING IS WANTED")
        if self.broadening_is_not_wanted:
            commands.append("BROADENING IS NOT WANTED")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = BroadeningOptions(
            broadening_is_wanted=True,
            broadening_is_not_wanted=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
