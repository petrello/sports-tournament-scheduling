# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM minizinc/minizinc:latest AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev git \
    wget curl unzip build-essential cmake python3-venv \
    software-properties-common ca-certificates gnupg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Install Z3 (CLI only)
# ------------------------------------------------------------------------------
RUN cd /tmp && \
    wget -q https://github.com/Z3Prover/z3/releases/download/z3-4.15.2/z3-4.15.2-x64-glibc-2.39.zip && \
    unzip -q z3-4.15.2-x64-glibc-2.39.zip && \
    mkdir -p /opt/z3/bin && \
    mv z3-4.15.2-x64-glibc-2.39/bin/z3 /opt/z3/bin/ && \
    chmod +x /opt/z3/bin/z3 && \
    rm -rf /tmp/z3*

# ------------------------------------------------------------------------------
# Install cvc5 (static build)
# ------------------------------------------------------------------------------
RUN cd /tmp && \
    wget -q https://github.com/cvc5/cvc5/releases/download/cvc5-1.3.0/cvc5-Linux-x86_64-static.zip && \
    unzip -q cvc5-Linux-x86_64-static.zip && \
    mkdir -p /opt/cvc5/bin && \
    mv cvc5-Linux-x86_64-static/bin/cvc5 /opt/cvc5/bin/ && \
    chmod +x /opt/cvc5/bin/cvc5 && \
    rm -rf /tmp/cvc5*

# ------------------------------------------------------------------------------
# Build and Install HiGHS from source
# ------------------------------------------------------------------------------
RUN cd /tmp && \
    # 1. Download the source code
    wget -q https://github.com/ERGO-Code/HiGHS/archive/refs/tags/v1.7.0.tar.gz -O HiGHS-1.7.0.tar.gz && \
    # 2. Extract the archive
    tar -xzf HiGHS-1.7.0.tar.gz && \
    cd HiGHS-1.7.0 && \
    # 3. Configure the build using CMake
    mkdir build && \
    cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    # 4. Compile and install the solver
    cmake --build . --parallel $(nproc) && \
    cmake --install . && \
    # 5. Clean up the source and build files
    rm -rf /tmp/HiGHS*

# ------------------------------------------------------------------------------
# Install CBC and GLPK
# ------------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    coinor-cbc glpk-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Set up Python virtual environment
# ------------------------------------------------------------------------------
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r /tmp/requirements.txt

# ==============================================================================
# Stage 2: Final Image
# ==============================================================================
FROM minizinc/minizinc:latest AS final

ENV DEBIAN_FRONTEND=noninteractive

# Install Python in final image so python3/pip commands work
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home appuser

# Copy Python environment and solver binaries from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /usr/local /usr/local
COPY --from=builder /opt/z3/bin/z3 /usr/bin/z3
COPY --from=builder /opt/cvc5/bin/cvc5 /usr/bin/cvc5
COPY --from=builder /usr/bin/cbc /usr/bin/cbc
COPY --from=builder /usr/bin/glpsol /usr/bin/glpsol
COPY --from=builder /usr/local/bin/highs /usr/local/bin/highs
COPY --from=builder /usr/lib/x86_64-linux-gnu/lib* /usr/lib/x86_64-linux-gnu/

# --- Configure the Dynamic Linker ---
RUN ldconfig

# Add the venv to the PATH for all users
ENV PATH="/opt/venv/bin:$PATH"

# --- Final Verification Step ---
RUN python3 --version && \
    pip --version && \
    minizinc --version && \
    z3 --version && \
    cvc5 --version && \
    cbc -quit | head -n 1 && \
    glpsol --version && \
    highs --version && \

# Set working directory
WORKDIR /home/appuser/cdmo

# Copy application source
COPY . .

# Set file ownership to appuser
RUN chown -R appuser:appgroup /home/appuser/cdmo

# Switch to non-root user
USER appuser

# Start interactive shell
CMD ["/bin/bash"]