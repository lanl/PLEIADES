Installation Guide
==================

This section provides detailed steps to install both SAMMY and the PLEIADES Python package.

Prerequisites
-------------

Before you begin, ensure you have the following prerequisites installed:

* **git**: A version control system used to clone repositories. You can install it using your system's package manager (e.g., `apt`, `yum`, `brew`, etc.).
* **pip**: A package installer for Python. It is included with Python installations, or you can install it via your system’s package manager.

Step-by-Step Installation
--------------------------

1. **Clone and Build SAMMY**

   First, you need to clone and install SAMMY. Follow the steps below:

   .. code-block:: bash

      git clone https://code.ornl.gov/RNSD/SAMMY.git

   Next, navigate to the SAMMY directory and build the package:

   .. code-block:: bash

      cd SAMMY/sammy
      mkdir myscript
      cp script/configure_sammy_gcc.sh myscript/
      mkdir build
      cd build
      ../myscript/configure_sammy_gcc.sh ../
      make -j4
      make install

2. **Verify SAMMY Installation (Optional)**

   To ensure that SAMMY has been installed correctly, open a new terminal and check if SAMMY is accessible by running the following command:

   .. code-block:: bash

      sammy

   If successful, the SAMMY command should execute without errors.

3. **Clone the PLEIADES Repository**

   After installing SAMMY, you can clone the PLEIADES repository from GitHub:

   .. code-block:: bash

      git clone https://github.com/lanl/PLEIADES

4. **Install the PLEIADES Package**

   Navigate to the cloned `Pleiades` repository and install the package using `pip`:

   .. code-block:: bash

      cd Pleiades
      pip install -e .

5. **Configure SAMMY Path**

   For PLEIADES to work correctly with SAMMY, you need to add SAMMY’s `bin` directory to your system’s PATH environment variable.

   1. Open your terminal and edit your shell configuration file (e.g., `.bashrc`, `.zshrc`, or `.bash_profile`).
   2. Add the following line, replacing `<SAMMY_INSTALL_DIR>` with the actual installation directory of SAMMY:

      .. code-block:: bash

         export PATH=$PATH:<SAMMY_INSTALL_DIR>/bin

   3. Apply the changes by sourcing the configuration file:

      .. code-block:: bash

         source ~/.bashrc  # Replace with your shell configuration file name

6. **Uninstalling PLEIADES (Optional)**

   If you ever need to uninstall the PLEIADES package, you can do so using `pip`:

   .. code-block:: bash

      pip uninstall pleiades

Troubleshooting
---------------

If you encounter issues during the installation of SAMMY or PLEIADES, refer to the following resources:

* **SAMMY Documentation**: Visit the `SAMMY website <https://code.ornl.gov/RNSD/SAMMY>`_ for installation and configuration guidance.
* **PLEIADES Documentation**: Refer to the `Read the Docs <https://pleiades-sammy.readthedocs.io/en/latest/>`_ page for more details on PLEIADES setup and usage.

Additional Notes
----------------

* You need to ensure that your SAMMY installation is properly accessible from your environment's PATH.
* Use a virtual environment or conda environment to manage Python dependencies effectively.

License
=======

This project is licensed under the MIT License. See the `LICENSE` file for more details.
