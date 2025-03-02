from pydantic import BaseModel, Field, model_validator
from typing import ClassVar

"""
    These notes are taken from the SAMMY manual. 
    - * denotes a default options
    - Mutually exclusive options are grouped together starting with -------------- and ending with -------------
    - options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Broadening options: 
    Is broadening wanted
    broadening_options = [ 
        --------------
        * "BROADENING IS WANTED",
        "BROADENING IS NOT WAnted"
        --------------
        ]

"""

class BroadeningOptions(BaseModel):
    """Model to enforce mutually exclusive selection of broadening options using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    broadening_is_wanted: bool = Field(default=True, description="BROADENING IS WANTED")
    broadening_is_not_wanted: bool = Field(default=False, description="BROADENING IS NOT WAnted")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: ClassVar[list[list[str]]] = [
        ["broadening_is_wanted", "broadening_is_not_wanted"]
    ]
    
    def __init__(self, **data):
        super().__init__(**data)
        for name, value in data.items():
            self.__setattr__(name, value)
        self.check_exclusivity()

    def __setattr__(self, name, value):
        """Custom setattr to handle mutually exclusive options."""
        for group in self.mutually_exclusive_groups:
            if name in group and value is True:
                for option in group:
                    if option != name:
                        self.__dict__[option] = False
        self.__dict__[name] = value

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.broadening_is_wanted:
            commands.append("BROADENING IS WANTED")
        if self.broadening_is_not_wanted:
            commands.append("BROADENING IS NOT WANTED")
        return commands

    def check_exclusivity(self):
        """Ensure that only one broadening option is selected using boolean flags."""
        for group in self.mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(self, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

# Example usage
try:
    options = BroadeningOptions(
        broadening_is_wanted=True,
    )
except ValueError as e:
    print(e)