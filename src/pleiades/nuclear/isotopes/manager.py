"""Manages access to isotope data files packaged with PLEIADES."""

import functools
import logging
import re
import requests
import zipfile
import io
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Set

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData