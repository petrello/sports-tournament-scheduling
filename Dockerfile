# ==============================================================================
# Stage 1: Builder
#
# Base image is minizinc/minizinc, which provides the full CP toolchain.
# This builder stage will add all SMT, MIP, and Python dependencies on top.
# ==============================================================================
FROM minizinc/minizinc:latest AS builder

# Set environment variables to prevent interactive prompts during installation
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# --- Install System Dependencies & Solvers ---
# This is done in a single RUN command to optimize Docker layer caching.
# The minizinc image is Debian-based, so we use apt-get.
RUN apt-get update && \
    # Install utilities needed for adding repositories and downloading files
    apt-get install -y --no-install-recommends \
        wget \
        gnupg \
        software-properties-common \
        ca-certificates \
        unzip \
        python3-venv && \
    \
    # --- SMT Solvers ---
    # 1. Install Z3 CLI (may already be present, but this ensures it)
    apt-get install -y --no-install-recommends z3 && \
    \
    # 2. Install CVC5 CLI from its official PPA for the latest version
    wget -qO- https://cvc5.github.io/cvc5-repo/keys/cvc5-official-key.asc | gpg --dearmor -o /usr/share/keyrings/cvc5-official-keyring.gpg && \
    # Detect Debian version for CVC5 repository
    . /etc/os-release && \
    echo "deb [signed-by=/usr/share/keyrings/cvc5-official-keyring.gpg] https://cvc5.github.io/cvc5-repo/debian/ $VERSION_CODENAME main" > /etc/apt/sources.list.d/cvc5-official.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends cvc5 && \
    \
    # --- MIP Solvers ---
    # 3. Install CBC and GLPK from Debian repositories
    apt-get install -y --no-install-recommends coinor-cbc glpk-utils && \
    \
    # 4. Install HiGHS by downloading the pre-compiled binary
    wget https://github.com/ERGO-Code/HiGHS/releases/download/v1.7.0/HiGHS-1.7.0-Linux.zip -O HiGHS.zip && \
    unzip HiGHS.zip && \
    mv ./HiGHS-1.7.0-Linux/bin/highs /usr/local/bin/highs && \
    chmod +x /usr/local/bin/highs && \
    \
    # --- Clean up ---
    rm -rf /var/lib/apt/lists/* HiGHS.zip HiGHS-1.7.0-Linux && \
    \
    # --- Install Python Dependencies ---
    # Create a virtual environment for clean package management
    python3 -m venv /opt/venv && \
    # Activate the venv for subsequent commands
    . /opt/venv/bin/activate && \
    # Upgrade pip
    pip install --upgrade pip && \
    # Copy only the requirements file to leverage caching
    COPY requirements.txt . && \
    # Install the Python packages
    pip install -r requirements.txt


# ==============================================================================
# Stage 2: Final Image
#
# This stage creates the final, lean image, also based on minizinc.
# We copy the venv and solvers from the builder, keeping the MiniZinc base.
# ==============================================================================
FROM minizinc/minizinc:latest AS final

ENV DEBIAN_FRONTEND=noninteractive

# --- Create a non-root user for security ---
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

# --- Copy Artifacts from Builder Stage ---
# Copy the Python virtual environment with all packages installed
COPY --from=builder /opt/venv /opt/venv
# Copy the installed solvers from the builder stage
COPY --from=builder /usr/bin/z3 /usr/bin/z3
COPY --from=builder /usr/bin/cvc5 /usr/bin/cvc5
COPY --from=builder /usr/bin/cbc /usr/bin/cbc
COPY --from=builder /usr/bin/glpsol /usr/bin/glpsol
COPY --from=builder /usr/local/bin/highs /usr/local/bin/highs

# Add the venv to the PATH for all users
# The minizinc image already sets a PATH, so we prepend to it
ENV PATH="/opt/venv/bin:$PATH"

# --- Final Verification Step ---
# This RUN command checks that all installed components are available and
# executable. If any command fails, the Docker build will stop.
RUN echo "--- Verifying Python and Pip installations ---" && \
    python3 --version && \
    pip --version && \
    echo "\n--- Verifying CP Solver installation ---" && \
    minizinc --version && \
    echo "\n--- Verifying SMT Solver installations ---" && \
    z3 --version && \
    cvc5 --version && \
    echo "\n--- Verifying MIP Solver installations ---" && \
    cbc -quit | head -n 1 && \
    glpsol --version && \
    highs --version && \
    echo "\n\n***************************************************" && \
    echo "* All solvers and tools installed successfully!  *" && \
    echo "***************************************************"

# Set the working directory
WORKDIR /home/appuser/cdmo

# Copy the project source code into the container
COPY . .

# Change ownership of the project files to the non-root user
RUN chown -R appuser:appgroup /home/appuser/cdmo

# Switch to the non-root user
USER appuser

# Set the default command to open a bash shell, as requested
CMD ["/bin/bash"]
