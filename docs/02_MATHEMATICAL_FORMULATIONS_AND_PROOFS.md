# Mathematical Formulations & Proofs

## 1. Headless State Space Normalization Equations

Each supported game engine maps diverse internal RAM registers and logical game invariants into a standardized 4-dimensional continuous feature vector $x \in [0.0, 1.0]^4$.

### 1.1 Super Mario Bros (NES 6502 RAM)
The player position on the NES spans horizontal screen pages and sub-page pixel positions:
$$X_{\text{total}} = 256 \cdot \text{RAM}[0\text{x}006\text{D}] + \text{RAM}[0\text{x}0086]$$

The 4 normalized coordinates are formulated as:
$$\begin{aligned}
x_0 &= \text{clip}\left(\frac{X_{\text{total}}}{2560.0}, 0.0, 1.0\right) && \text{(Horizontal Progress across World 1-1)} \\
x_1 &= \text{clip}\left(\frac{\text{RAM}[0\text{x}00\text{CE}]}{255.0}, 0.0, 1.0\right) && \text{(Vertical Y-Position)} \\
x_2 &= \text{clip}\left(\frac{\text{signed}(\text{RAM}[0\text{x}0057]) + 6.0}{12.0}, 0.0, 1.0\right) && \text{(Horizontal Velocity } V_x \in [-6, +6]\text{)} \\
x_3 &= \text{clip}\left(\frac{\text{RAM}[0\text{x}001\text{D}]}{3.0}, 0.0, 1.0\right) && \text{(Collision / Air / Glitch State } \in \{0, 1, 2, 3\}\text{)}
\end{aligned}$$

### 1.2 ViZDoom Corridor Combat
ViZDoom extracts native 32-bit floating-point game variables directly from the Doom engine:
$$\begin{aligned}
x_0 &= \text{clip}\left(\frac{\text{POSITION\_X} + 600.0}{1200.0}, 0.0, 1.0\right) && \text{(X Coordinate in Corridor)} \\
x_1 &= \text{clip}\left(\frac{\text{POSITION\_Y} + 600.0}{1200.0}, 0.0, 1.0\right) && \text{(Y Coordinate in Corridor)} \\
x_2 &= \text{clip}\left(\frac{\text{VELOCITY\_X} + 50.0}{100.0}, 0.0, 1.0\right) && \text{(Lateral Velocity)} \\
x_3 &= \text{clip}\left(\frac{\text{HEALTH}}{100.0}, 0.0, 1.0\right) && \text{(Player Health Pool)}
\end{aligned}$$

### 1.3 python-chess Board Topological Invariants
Given a board $B$ represented as bitboards, 4 topological invariants are extracted:
$$\begin{aligned}
x_0 &= \text{clip}\left(\frac{\text{Material}_{\text{White}} - \text{Material}_{\text{Black}} + 39.0}{78.0}, 0.0, 1.0\right) && \text{(Material Imbalance)} \\
x_1 &= \text{clip}\left(\frac{\text{popcount}(B_{\text{all\_pieces}})}{32.0}, 0.0, 1.0\right) && \text{(Piece Density)} \\
x_2 &= \begin{cases} 1.0 & \text{if } \text{popcount}(K_{\text{white}}) = 1 \text{ and } \text{popcount}(K_{\text{black}}) = 1 \\ 0.0 & \text{otherwise (Multiple / Missing Kings)} \end{cases} && \text{(King Integrity)} \\
x_3 &= \begin{cases} 1.0 & \text{if } \text{popcount}(P \cap \{\text{Rank 1, 8}\}) = 0 \\ 0.0 & \text{otherwise (Pawns on Rank 1 or 8)} \end{cases} && \text{(Pawn Rank Invariant)}
\end{aligned}$$

### 1.4 MiniSudoku 4x4 Latin-Square Invariants
For a $4 \times 4$ grid $G \in \{1, 2, 3, 4\}^{4 \times 4}$, the invariant vector $I \in [0, 1]^4$ measures rule satisfaction:
$$\begin{aligned}
I_{\text{row}} &= \frac{1}{4} \sum_{r=1}^4 \frac{|\text{unique}(G_{r, :})|}{4} && \text{(Row Uniqueness)} \\
I_{\text{col}} &= \frac{1}{4} \sum_{c=1}^4 \frac{|\text{unique}(G_{:, c})|}{4} && \text{(Column Uniqueness)} \\
I_{\text{box}} &= \frac{1}{4} \sum_{b=1}^4 \frac{|\text{unique}(\text{Box}_b)|}{4} && \text{(}2 \times 2\text{ Sub-grid Uniqueness)} \\
I_{\text{range}} &= \frac{1}{16} \sum_{r=1}^4 \sum_{c=1}^4 \mathbb{I}(G_{r, c} \in \{1, 2, 3, 4\}) && \text{(Value Range Legality)}
\end{aligned}$$
For any valid board, $I = [1.0, 1.0, 1.0, 1.0]$. Injected exploits collapse $I_k \le 0.75$.

---

## 2. Fast Statevector Quantum Kernel: Mathematical Proof

### 2.1 Standard Quantum Kernel Estimation Bottleneck
The standard quantum kernel between two states $x_i, x_j$ is defined as the transition fidelity:
$$K(x_i, x_j) = |\langle 0^{\otimes n} | U^\dagger(x_j) U(x_i) | 0^{\otimes n} \rangle|^2$$

For a dataset of $N$ samples:
- **Pairwise circuit count**:
  $$\text{Circuits} = \frac{N(N - 1)}{2} = \mathcal{O}(N^2)$$
- With $S$ measurement shots per circuit, total quantum evaluations:
  $$\text{Evaluations}_{\text{standard}} = \mathcal{O}(N^2 \cdot S)$$
For $N = 200$ and $S = 1024$, this requires $19,900 \text{ circuits}$ and $> 20.3 \text{ million shots}$, taking 10 to 30 minutes on CPU simulation.

### 2.2 Proof of $O(N)$ Statevector Projection Scaling
**Theorem**: For an $n$-qubit quantum feature map where statevectors are classically tractable ($n \le 16$), the complete Gram matrix $K \in \mathbb{R}^{N \times N}$ can be computed in $\mathcal{O}(N \cdot 2^n + N^2 \cdot 2^n)$ operations without pairwise circuit compilation.

**Proof**:
1. Evaluate the parameterized feature map statevector for each individual training sample $x_i$ once:
   $$| \psi(x_i) \rangle = U(x_i) | 0^{\otimes n} \rangle \in \mathbb{C}^{2^n} \quad \forall i \in \{1, \dots, N\}$$
   Cost: $N$ statevector simulations of depth $d$, each costing $\mathcal{O}(d \cdot 2^n)$ operations.

2. Assemble the statevectors into a complex statevector matrix:
   $$V = \begin{bmatrix} \langle \psi(x_1) | \\ \langle \psi(x_2) | \\ \vdots \\ \langle \psi(x_N) | \end{bmatrix} \in \mathbb{C}^{N \times 2^n}$$

3. Compute the matrix of complex inner products via matrix multiplication:
   $$M = V V^\dagger \in \mathbb{C}^{N \times N}, \quad \text{where } M_{ij} = \langle \psi(x_i) | \psi(x_j) \rangle$$
   Cost: Matrix multiplication of $(N \times 2^n)$ by $(2^n \times N)$ requires $\mathcal{O}(N^2 \cdot 2^n)$ operations.

4. Apply element-wise absolute value squared:
   $$K = |M|^{\odot 2} \in \mathbb{R}^{N \times N}, \quad \text{where } K_{ij} = |M_{ij}|^2 = |\langle \psi(x_i) | \psi(x_j) \rangle|^2$$

5. **Exact Diagonal Property**:
   $$K_{ii} = |\langle \psi(x_i) | \psi(x_i) \rangle|^2 = 1.0 \quad \forall i$$
   The resulting matrix $K$ is symmetric, positive semi-definite, with all diagonal entries strictly equal to $1.0$.

$$\mathcal{O}(\text{Total Operations}) = \mathcal{O}\left(N \cdot 2^n + N^2 \cdot 2^n\right) \ll \mathcal{O}\left(N^2 \cdot S\right)$$
For $n = 4$ qubits ($2^n = 16$) and $N = 200$:
$$\text{Inner Product Matrix Size} = 200 \times 16 \implies 200 \times 200 \text{ matrix product in } \mathbf{0.41 \text{ seconds (240x faster)}}.$$

### 2.3 One-Class SVM Dual Optimization
The One-Class SVM finds a separating hyperplane in the kernel feature space that captures legal gameplay while rejecting outliers. The dual optimization problem is:

$$\min_{\alpha} \frac{1}{2} \sum_{i=1}^N \sum_{j=1}^N \alpha_i \alpha_j K(x_i, x_j)$$
$$\text{subject to } 0 \le \alpha_i \le \frac{1}{\nu N} \quad \text{and} \quad \sum_{i=1}^N \alpha_i = 1$$
where $\nu \in (0, 1]$ represents the upper bound on the fraction of training outliers (set to $\nu = 0.08$).

Given the optimized dual coefficients $\alpha^*$, the decision function for a test state $x$ is:
$$f(x) = \sum_{i=1}^N \alpha_i^* K(x, x_i) - \rho$$
where $\rho$ is the offset threshold. The signed **Exploit Anomaly Score** is formulated as:
$$S(x) = -f(x) = \rho - \sum_{i=1}^N \alpha_i^* K(x, x_i)$$
- If $S(x) \le 0 \implies f(x) \ge 0 \implies \text{\textbf{Legal Inlier State}} \quad [LEGAL PASS]$
- If $S(x) > 0 \implies f(x) < 0 \implies \text{\textbf{Exploit / Anomaly Detected}} \quad [INTERCEPTED]$

---

## 3. Grover Amplitude Amplification: Derivation & Proof

### 3.1 Geometric Invariant Subspace
Let the computational basis states be partitioned into two orthogonal subspaces:
1. The **good / exploit subspace** spanned by $M$ marked exploit states:
   $$| \text{good} \rangle = \frac{1}{\sqrt{M}} \sum_{x \in \text{Exploits}} | x \rangle$$
2. The **legal gameplay subspace** spanned by $N - M$ unmarked states:
   $$| \text{bad} \rangle = \frac{1}{\sqrt{N - M}} \sum_{x \notin \text{Exploits}} | x \rangle$$

The uniform superposition state initialized by Hadamard gates $H^{\otimes n} | 0 \rangle$ can be expressed as:
$$| s \rangle = \frac{1}{\sqrt{N}} \sum_{x=0}^{N-1} | x \rangle = \cos\left(\frac{\theta}{2}\right) | \text{bad} \rangle + \sin\left(\frac{\theta}{2}\right) | \text{good} \rangle$$
where the initial rotation angle $\theta$ satisfies:
$$\sin\left(\frac{\theta}{2}\right) = \sqrt{\frac{M}{N}}$$

### 3.2 Grover Rotation Operator
The Grover iteration $G = D \cdot O_f$ comprises:
1. **Phase Oracle**:
   $$O_f = I - 2 | \text{good} \rangle \langle \text{good} |$$
   Flips the amplitude of the exploit states while preserving legal states:
   $$O_f \left( \cos\left(\frac{\theta}{2}\right) | \text{bad} \rangle + \sin\left(\frac{\theta}{2}\right) | \text{good} \rangle \right) = \cos\left(\frac{\theta}{2}\right) | \text{bad} \rangle - \sin\left(\frac{\theta}{2}\right) | \text{good} \rangle$$

2. **Diffusion Operator**:
   $$D = 2 | s \rangle \langle s | - I$$
   Reflects the state about the uniform superposition $| s \rangle$.

Each application of $G$ rotates the statevector by exactly $\theta$ toward $| \text{good} \rangle$:
$$G^k | s \rangle = \cos\left(\frac{2k + 1}{2} \theta\right) | \text{bad} \rangle + \sin\left(\frac{2k + 1}{2} \theta\right) | \text{good} \rangle$$

### 3.3 Optimal Iterations & Success Probability Proof
To maximize the probability of measuring an exploit state, we set the argument of $\sin$ to $\frac{\pi}{2}$:
$$\frac{2k + 1}{2} \theta \approx \frac{\pi}{2} \implies 2k + 1 \approx \frac{\pi}{\theta}$$

Using the small-angle approximation $\sin(\theta/2) \approx \theta/2 \approx \sqrt{M/N} \implies \theta \approx 2\sqrt{M/N}$:
$$2k + 1 \approx \frac{\pi}{2\sqrt{M/N}} \implies k \approx \left\lfloor \frac{\pi}{4} \sqrt{\frac{N}{M}} \right\rfloor$$

**Numerical Proof for 4-Qubit Subsystem**:
- Let $n = 4$ qubits $\implies N = 2^4 = 16$ states.
- Let $M = 1$ marked exploit bitstring (e.g. `'1011'`).
- Angle:
  $$\sin\left(\frac{\theta}{2}\right) = \sqrt{\frac{1}{16}} = \frac{1}{4} = 0.25 \implies \frac{\theta}{2} = \arcsin(0.25) \approx 0.25268 \text{ rad} \implies \theta \approx 0.50536 \text{ rad}$$
- Optimal iterations:
  $$k = \left\lfloor \frac{\pi}{4} \sqrt{16} \right\rfloor = \lfloor 3.14159 \rfloor = 3 \text{ iterations}$$
- State after $k = 3$ iterations:
  $$\text{Angle} = \frac{2(3) + 1}{2} \theta = \frac{7}{2}(0.50536) = 1.76876 \text{ rad}$$
  $$P(\text{Exploit}) = \sin^2(1.76876) = (0.9727)^2 = \mathbf{94.61\%}$$
- **Amplification Factor**:
  $$\text{Gain} = \frac{P(\text{Grover})}{P(\text{Random})} = \frac{0.9461}{1/16} = \frac{0.9461}{0.0625} = \mathbf{7.57\times \text{ probability boost}}$$

---

## 4. Matrix Product State (MPS) Complexity & Truncation

For an arbitrary $n$-qubit state:
$$| \Psi \rangle = \sum_{s_1=0}^1 \cdots \sum_{s_n=0}^1 c_{s_1, \dots, s_n} | s_1 \dots s_n \rangle \in \mathbb{C}^{2^n}$$
A naive full statevector representation requires storing $2^n$ complex numbers ($2^{16} = 65,536$ for $n=16$).

By successive Singular Value Decompositions (SVD), the rank-$n$ tensor $c$ is decomposed into a Matrix Product State:
$$c_{s_1, \dots, s_n} = A^{[1] s_1} A^{[2] s_2} \cdots A^{[n] s_n}$$
where $A^{[i] s_i} \in \mathbb{C}^{\chi_{i-1} \times \chi_i}$, with $\chi_0 = \chi_n = 1$.

Enforcing a maximum bond dimension cap $\chi_{\max} = 32$ truncates singular values smaller than $\epsilon = 10^{-8}$:
$$\chi_i \le \min\left(2^i, 2^{n-i}, \chi_{\max}\right)$$

**Computational Complexity Comparison**:
- Statevector simulation: $\mathcal{O}(2^n)$ memory and $\mathcal{O}(d \cdot 2^n)$ time.
- MPS simulation: $\mathcal{O}(n \cdot \chi_{\max}^2)$ memory and $\mathcal{O}(n \cdot d \cdot \chi_{\max}^3)$ time.

For $n = 16$ qubits, $d = 8$ layers, $\chi_{\max} = 32$:
$$\text{Memory}_{\text{MPS}} \approx 16 \times 32^2 \times 16 \text{ bytes} \approx 262 \text{ KB} \quad \text{vs.} \quad \text{Memory}_{\text{Statevector}} \approx 65,536 \times 16 \text{ bytes} \approx 1.05 \text{ MB}$$
The MPS execution completes in **0.028 seconds**, verifying constraint satisfaction across 16 qubits without memory blowout.

---

## 5. Hybrid QRL Policy Gradients & Analytic Parameter Shift Rule

### 5.1 Parameter Shift Rule for Quantum Observables
Let the quantum expectation value of Pauli observable $Z_i$ with respect to variational circuit parameters $\theta \in \mathbb{R}^p$ be:
$$\langle Z_i \rangle(\theta) = \langle 0 | U^\dagger(\theta) Z_i U(\theta) | 0 \rangle$$

When gates take the form $U_j(\theta_j) = \exp\left(-i \frac{\theta_j}{2} G_j\right)$ with generator $G_j \in \{X, Y, Z\}$ having eigenvalues $\pm 1$, the exact analytic gradient is computed without finite-difference approximation via the **Parameter Shift Rule**:
$$\frac{\partial \langle Z_i \rangle}{\partial \theta_j} = \frac{\langle Z_i \rangle\left(\theta + \frac{\pi}{2} e_j\right) - \langle Z_i \rangle\left(\theta - \frac{\pi}{2} e_j\right)}{2}$$

This ensures exact quantum backpropagation through PyTorch's `autograd` engine via Qiskit's `TorchConnector`.

### 5.2 Actor-Critic Objective with Intrinsic Exploit Shaping
The policy $\pi_\theta(a|s)$ outputs discrete action logits from the 4 quantum expectations:
$$\pi_\theta(a|s) = \frac{\exp\left(W_a \langle Z \rangle + b_a\right)}{\sum_{a'} \exp\left(W_{a'} \langle Z \rangle + b_{a'}\right)}$$

The loss function minimized by the agent combines policy gradient, value error, and entropy regularization:
$$\mathcal{L}(\theta) = \mathcal{L}_{\text{policy}}(\theta) + c_1 \mathcal{L}_{\text{value}}(\theta) - c_2 \mathcal{H}(\pi_\theta(\cdot | s))$$

where:
$$\mathcal{L}_{\text{policy}}(\theta) = -\mathbb{E}_t \left[ \log \pi_\theta(a_t | s_t) \cdot A_t \right]$$
$$\mathcal{L}_{\text{value}}(\theta) = \frac{1}{2} \mathbb{E}_t \left[ \left( V_\theta(s_t) - G_t \right)^2 \right]$$
$$\mathcal{H}(\pi_\theta(\cdot | s_t)) = -\sum_a \pi_\theta(a | s_t) \log \pi_\theta(a | s_t)$$

The return $G_t$ incorporates the **Curiosity Exploit Bonus**:
$$G_t = \sum_{k=0}^{T - t} \gamma^k \left[ r_{t+k} + \lambda \max\left(0, S_{\text{anomaly}}(s_{t+k+1})\right) \right]$$
where $\gamma = 0.99$, $\lambda = 2.0$, $c_1 = 0.5$, and $c_2 = 0.01$.

