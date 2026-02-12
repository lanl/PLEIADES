Installation
============

This guide covers installing PLEIADES and its prerequisites.

Prerequisites
-------------

PLEIADES is a Python interface to `SAMMY <https://code.ornl.gov/RNSD/SAMMY>`_,
a Fortran code for neutron resonance analysis. Depending on which backend you
plan to use, you may need to install SAMMY separately.

**Backend Requirements:**

- **Local backend**: Requires SAMMY installed and available in your PATH
- **Docker backend**: Requires Docker installed and running
- **NOVA backend**: Requires NOVA credentials (no local SAMMY installation needed)

.. note::

   SAMMY is external software maintained by Oak Ridge National Laboratory.
   For SAMMY installation instructions, refer to the
   `SAMMY documentation <https://code.ornl.gov/RNSD/SAMMY>`_.

User Installation
-----------------

Install from PyPI (recommended for most users):

.. code-block:: bash

   pip install pleiades-neutron

Or from conda-forge:

.. code-block:: bash

   conda install -c conda-forge pleiades-neutron

NOVA Backend (Optional - Currently Paused)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    NOVA backend support is currently paused while the NOVA API stabilizes.
    The installation instructions below are retained for future use.

To use the NOVA web service backend, install with the ``nova`` extra:

.. code-block:: bash

   pip install pleiades-neutron[nova]

This installs the ``nova-galaxy`` package required for NOVA integration.

Developer Installation
----------------------

For contributing to PLEIADES or running from source:

**Prerequisites:**

- ``git``: Version control system
- ``pixi``: Package manager (`installation guide <https://pixi.sh/latest/>`_)

**Steps:**

1. **Clone the PLEIADES repository:**

   .. code-block:: bash

      git clone https://github.com/lanl/PLEIADES.git
      cd PLEIADES

2. **Install using Pixi:**

   .. code-block:: bash

      pixi install

   This creates an isolated environment with all dependencies.

3. **Verify installation:**

   .. code-block:: bash

      pixi run post_install_check

   This checks if SAMMY is accessible (required for local backend only).

4. **Configure SAMMY path (local backend only):**

   Add SAMMY's ``bin`` directory to your PATH:

   .. code-block:: bash

      export PATH=$PATH:/path/to/sammy/bin

   Add this to your shell configuration file (e.g., ``~/.bashrc``) to persist.

Development Tasks
^^^^^^^^^^^^^^^^^

PLEIADES provides several Pixi tasks for development:

.. code-block:: bash

   # Run tests
   pixi run test

   # Build documentation
   pixi run build-docs

   # Format code
   pixi run format

   # Run linting checks
   pixi run lint

   # Install pre-commit hooks
   pixi run pre-commit-install

Available Environments
^^^^^^^^^^^^^^^^^^^^^^

Two Pixi environments are available:

- ``default``: Development environment with testing and linting tools
- ``jupyter``: Includes JupyterLab for interactive notebook work

Activate the Jupyter environment:

.. code-block:: bash

   pixi shell -e jupyter

Verifying Installation
----------------------

After installation, verify PLEIADES is working:

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory

   # Check available backends
   available = SammyFactory.list_available_backends()
   for backend, is_available in available.items():
       status = "available" if is_available else "not available"
       print(f"{backend.value}: {status}")

This will show which backends are configured and ready to use.

Troubleshooting
---------------

**SAMMY not found (local backend):**
   Ensure SAMMY is installed and its ``bin`` directory is in your PATH.
   Run ``which sammy`` to verify.

**Docker backend unavailable:**
   Ensure Docker is installed and running. Run ``docker info`` to verify.

**NOVA backend unavailable:**
   Set the required environment variables:

   .. code-block:: bash

      export NOVA_URL="https://your-nova-server"
      export NOVA_API_KEY="your-api-key"

**Import errors:**
   Ensure you're using Python 3.10 or later:

   .. code-block:: bash

      python --version
