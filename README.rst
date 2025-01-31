PLEIADES
========
.. image:: https://results.pre-commit.ci/badge/github/lanl/PLEIADES/main.svg
   :target: https://results.pre-commit.ci/latest/github/lanl/PLEIADES/main
   :alt: pre-commit.ci status

.. image:: https://readthedocs.org/projects/example-sphinx-basic/badge/?version=latest
   :target: https://pleiades-sammy.readthedocs.io/en/latest/
   :alt: Documentation Status

.. image:: https://zenodo.org/badge/97755175.svg
   :target: https://zenodo.org/records/12729688
   :alt: DOI

.. This README.rst should work on Github and is also included in the Sphinx documentation project in docs/ - therefore, README.rst uses absolute links for most things so it renders properly on GitHub

PLEIADES' user documentation
============================

**PLEIADES:**
Python Libraries Extensions for Isotopic Analysis via Detailed Examination of SAMMY.
This is a Python package that sets up, executes, and analyzes, SAMMY runs.
If you are unfamiliar with SAMMY, please see the `SAMMY website <https://code.ornl.gov/RNSD/SAMMY>`_.

The user documentation can be found at `Read the Docs <https://pleiades-sammy.readthedocs.io/en/latest/>`_.

Installation
============

**Prerequisites:**

* ``git``: A version control system used to clone the SAMMY repository. You can usually install it using your system's package manager.
* ``pip``: A package installer for Python. You can usually install it using your system's package manager.

**Steps:**

1. **Clone and build the SAMMY Repository:**

   Use ``git`` to clone the SAMMY repository from GitLab:

   .. code-block:: bash

      git clone https://code.ornl.gov/RNSD/SAMMY.git


2. **Build and Install SAMMY:**

   Navigate to the cloned SAMMY directory (``SAMMY/sammy``) and follow the SAMMY installation instructions to build and install it. Refer to the SAMMY documentation for specific instructions.


   .. code-block:: bash

      cd SAMMY/sammy
      mkdir myscript
      cp script/configure_sammy_gcc.sh myscript/
      mkdir build
      cd build
      ../myscript/configure_sammy_gcc.sh ../
      make -j4
      make install

3. **Verification (Optional):**

   Open a new terminal window and check if the SAMMY executables are accessible. You can try running a SAMMY command, such as ``sammy``. If successful, the command should execute.

4. **Clone the PLEIADES Repository:**

   Use ``git`` to clone the ``pleiades`` repository from GitHub:

   .. code-block:: bash

      git clone https://github.com/along4/Pleiades

5. **Navigate to the Directory:**

   Change directories to the cloned `pleiades` repository:

   .. code-block:: bash

      cd Pleiades

6. **Install the Package:**

   Use ``pip`` to install the ``pleiades`` package:

   .. code-block:: bash

      pip install -e .

   Alternatively, you can use ``poetry`` to install the package. First, install ``poetry`` using the following command:

   .. code-block:: bash

      pip install poetry

   Use ``poetry`` to install the ``pleiades`` package:

   .. code-block:: bash

      poetry install

   Then run the following command to perform the post-installation check after sammy is installed:

   .. code-block:: bash

      poetry run post_install_check

   Using Poetry is recommended for managing dependencies and virtual environments, especially if you are working with multiple Python projects sharing the same base Python installation.

7. **Add SAMMY's bin Directory to PATH:**

   You'll need to add the ``bin`` directory of the installed SAMMY package to your system's PATH environment variable.
   This allows ``pleiades`` to locate the necessary SAMMY executables.

   - Open your terminal and edit your shell configuration file (e.g., ``.bashrc`` for Bash).
   - Add the following line (replace ``<SAMMY_INSTALL_DIR>`` with the actual installation directory of SAMMY):

     .. code-block:: bash

        export PATH=$PATH:<SAMMY_INSTALL_DIR>/bin

   - Save the changes and source the configuration file to apply the changes immediately:

     .. code-block:: bash

        source ~/.bashrc  # Replace with your shell configuration file name


**Troubleshooting:**

   * If you encounter issues during the SAMMY installation or path configuration, refer to the SAMMY documentation for specific guidance.

**Additional Notes:**

* You can uninstall ``pleiades`` using ``pip uninstall pleiades``.

License
=======

This project is licensed under the MIT License - see the `LICENSE <LICENSE>`_ file for details.
