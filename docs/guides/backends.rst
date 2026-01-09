Backend Selection Guide
=======================

PLEIADES supports three backends for executing SAMMY. This guide helps
you choose and configure the right backend for your use case.

Backend Comparison
------------------

=============== =================== =================== ===================
Feature         Local               Docker              NOVA
=============== =================== =================== ===================
Speed           Fastest             Medium              Slowest (network)
Setup           SAMMY installation  Docker installed    Credentials only
Isolation       None                Container           Full (remote)
Portability     OS-dependent        High                Highest
Offline use     Yes                 Yes                 No
=============== =================== =================== ===================

**Recommendations:**

- **Local**: Best for production workloads where SAMMY is installed
- **Docker**: Best for portability and reproducibility
- **NOVA**: Best when no local installation is possible

Checking Availability
---------------------

Use :meth:`~pleiades.sammy.factory.SammyFactory.list_available_backends` to
check which backends are configured:

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory

   available = SammyFactory.list_available_backends()
   for backend, is_available in available.items():
       print(f"{backend.value}: {'yes' if is_available else 'no'}")

Output example:

.. code-block:: text

   local: yes
   docker: yes
   nova: no

Local Backend
-------------

The local backend executes SAMMY directly on your system.

**Requirements:**
   - SAMMY executable in PATH or explicit path provided

**Detection:**
   Checks if ``sammy`` is found via ``shutil.which()``.

**Configuration:**

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory

   runner = SammyFactory.create_runner(
       backend_type="local",
       working_dir=Path("./work"),
       sammy_executable="sammy",      # default: "sammy" (uses PATH)
       shell_path=Path("/bin/bash"),  # default: /bin/bash
   )

**Environment variables:**

The local backend automatically sets ``LD_LIBRARY_PATH`` to include
``/usr/lib64`` for SAMMY's library dependencies.

Docker Backend
--------------

The Docker backend runs SAMMY in a container.

**Requirements:**
   - Docker installed and running
   - SAMMY Docker image available

**Detection:**
   Checks if ``docker`` command exists and ``docker info`` succeeds.

**Configuration:**

.. code-block:: python

   runner = SammyFactory.create_runner(
       backend_type="docker",
       working_dir=Path("./work"),
       image_name="kedokudo/sammy-docker",  # default
       container_working_dir=Path("/sammy/work"),  # default
       container_data_dir=Path("/sammy/data"),     # default
   )

**How it works:**

1. Mounts your working directory to ``/sammy/work`` in the container
2. Mounts the input file directory to ``/sammy/data``
3. Runs the ``sammy`` command inside the container
4. Outputs appear in your working directory

NOVA Backend
------------

The NOVA backend submits SAMMY jobs to a remote web service.

**Requirements:**
   - NOVA credentials (URL and API key)
   - Optional: ``nova-galaxy`` package (``pip install pleiades-neutron[nova]``)

**Detection:**
   Checks for ``NOVA_URL`` and ``NOVA_API_KEY`` environment variables.

**Configuration:**

.. code-block:: python

   runner = SammyFactory.create_runner(
       backend_type="nova",
       working_dir=Path("./work"),
       url="https://nova.example.com",  # or from NOVA_URL env var
       api_key="your-api-key",          # or from NOVA_API_KEY env var
       tool_id="neutrons_imaging_sammy",  # default
       timeout=3600,                      # default: 1 hour
   )

**Environment variable configuration:**

.. code-block:: bash

   export NOVA_URL="https://nova.example.com"
   export NOVA_API_KEY="your-api-key"

Then credentials can be omitted:

.. code-block:: python

   runner = SammyFactory.create_runner(
       backend_type="nova",
       working_dir=Path("./work"),
   )

**How it works:**

1. Uploads input files to NOVA service
2. Submits SAMMY execution request
3. Downloads results (as ZIP archive)
4. Extracts output files to output directory

YAML Configuration
------------------

All backends can be configured via YAML file:

.. code-block:: yaml

   # sammy_config.yaml
   backend: local  # or "docker" or "nova"
   working_dir: /path/to/work
   output_dir: /path/to/output

   local:
     sammy_executable: /opt/sammy/bin/sammy
     shell_path: /bin/bash

   docker:
     image_name: kedokudo/sammy-docker
     container_working_dir: /sammy/work
     container_data_dir: /sammy/data

   nova:
     url: ${NOVA_URL}
     api_key: ${NOVA_API_KEY}
     tool_id: neutrons_imaging_sammy
     timeout: 3600

Load with :meth:`~pleiades.sammy.factory.SammyFactory.from_config`:

.. code-block:: python

   runner = SammyFactory.from_config("sammy_config.yaml")

Environment variables (``${VAR_NAME}``) are automatically expanded.

Auto-Selection Logic
--------------------

:meth:`~pleiades.sammy.factory.SammyFactory.auto_select` tries backends
in this order:

1. **Local** - fastest, simplest
2. **Docker** - portable, isolated
3. **NOVA** - no local installation needed

If a ``preferred_backend`` is specified, it's tried first:

.. code-block:: python

   # Try docker first, fall back to others if unavailable
   runner = SammyFactory.auto_select(
       working_dir=Path("./work"),
       preferred_backend="docker",
   )

Backend-Specific Exceptions
---------------------------

:class:`~pleiades.sammy.factory.BackendNotAvailableError`
   Raised when the requested backend is not available.

:class:`~pleiades.sammy.factory.ConfigurationError`
   Raised when configuration is invalid (missing fields, bad paths, etc.).

.. code-block:: python

   from pleiades.sammy.factory import (
       SammyFactory,
       BackendNotAvailableError,
       ConfigurationError,
   )

   try:
       runner = SammyFactory.create_runner(
           backend_type="local",
           working_dir=Path("./work"),
       )
   except BackendNotAvailableError:
       print("Local SAMMY not found, trying Docker...")
       runner = SammyFactory.create_runner(
           backend_type="docker",
           working_dir=Path("./work"),
       )
