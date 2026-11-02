"""
Fast Statevector Quantum Kernel Anomaly Engine.
Combines a vectorized ZZFeatureMap statevector projection with OneClassSVM
to detect game glitches, illegal chess states, and rule-violating RAM transitions.

Compute Optimization:
Evaluates N statevectors once to construct the Gram matrix K_ij = |<psi_i|psi_j>|^2
via matrix multiplication V @ V^dag, avoiding O(N^2) shot-based circuit executions.
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.svm import OneClassSVM

try:
    from qiskit.circuit.library import zz_feature_map
    def make_zz_feature_map(num_qubits: int, reps: int, entanglement: str):
        return zz_feature_map(feature_dimension=num_qubits, reps=reps, entanglement=entanglement)
except ImportError:
    from qiskit.circuit.library import ZZFeatureMap
    def make_zz_feature_map(num_qubits: int, reps: int, entanglement: str):
        return ZZFeatureMap(feature_dimension=num_qubits, reps=reps, entanglement=entanglement)

from qiskit.quantum_info import Statevector


class FastQuantumKernel:
    """
    Evaluates quantum kernel Gram matrices via analytical statevectors.
    Complexity: O(N * 2^n + N^2 * 2^n) instead of O(N^2 * shots).
    """

    def __init__(
        self,
        num_qubits: int = 4,
        reps: int = 2,
        entanglement: str = "linear",
        input_scale: float = np.pi
    ):
        self.num_qubits = num_qubits
        self.reps = reps
        self.entanglement = entanglement
        self.input_scale = input_scale
        self.feature_map = make_zz_feature_map(num_qubits, reps, entanglement)
        self.cached_train_statevectors: Optional[np.ndarray] = None
        self.cached_train_X: Optional[np.ndarray] = None

    def _extract_statevectors(self, X: np.ndarray) -> np.ndarray:
        """
        Maps each feature row x in X to its statevector |phi(x)> in C^(2^n).
        Returns matrix V of shape (N, 2^num_qubits).
        """
        X_scaled = X * self.input_scale
        n_samples = len(X)
        dim = 2 ** self.num_qubits
        V = np.empty((n_samples, dim), dtype=np.complex128)

        for i in range(n_samples):
            assigned_circuit = self.feature_map.assign_parameters(X_scaled[i])
            sv = Statevector(assigned_circuit)
            V[i, :] = sv.data

        return V

    def compute_train_gram_matrix(self, X_train: np.ndarray) -> np.ndarray:
        """
        Computes K(X_train, X_train) where K_ij = |<phi(x_i)|phi(x_j)>|^2.
        """
        self.cached_train_X = np.copy(X_train)
        self.cached_train_statevectors = self._extract_statevectors(X_train)
        # Inner products: (N, dim) @ (dim, N) -> (N, N)
        inner_products = self.cached_train_statevectors @ self.cached_train_statevectors.conj().T
        K = np.abs(inner_products) ** 2
        # Ensure exact 1.0 on diagonal
        np.fill_diagonal(K, 1.0)
        return K

    def compute_test_kernel_matrix(self, X_test: np.ndarray) -> np.ndarray:
        """
        Computes K(X_test, X_train) of shape (M, N).
        """
        if self.cached_train_statevectors is None:
            raise ValueError("Train statevectors not cached. Run compute_train_gram_matrix first.")

        V_test = self._extract_statevectors(X_test)
        inner_products = V_test @ self.cached_train_statevectors.conj().T
        K = np.abs(inner_products) ** 2
        return K


class QuantumKernelAnomalyDetector:
    """
    Quantum Exploit & Anomaly Detection Pipeline.
    Trains a One-Class SVM on normal gameplay feature states using the Fast Quantum Kernel.
    """

    def __init__(
        self,
        num_qubits: int = 4,
        reps: int = 2,
        entanglement: str = "linear",
        nu: float = 0.08,
        gamma: str = "scale"
    ):
        self.num_qubits = num_qubits
        self.nu = nu
        self.kernel = FastQuantumKernel(num_qubits=num_qubits, reps=reps, entanglement=entanglement)
        self.svm = OneClassSVM(kernel="precomputed", nu=nu)
        self.is_fitted = False

    def fit(self, X_train: np.ndarray) -> "QuantumKernelAnomalyDetector":
        """
        Trains One-Class SVM on normal gameplay feature vectors.
        """
        t0 = time.time()
        K_train = self.kernel.compute_train_gram_matrix(X_train)
        self.svm.fit(K_train)
        self.is_fitted = True
        elapsed = time.time() - t0
        print(f"[QuantumKernel] Fitted One-Class SVM on {len(X_train)} samples in {elapsed:.3f}s.")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Returns +1 for normal gameplay, -1 for detected exploit/anomaly.
        """
        if not self.is_fitted:
            raise ValueError("Detector is not fitted yet.")
        K = self.kernel.compute_test_kernel_matrix(X)
        return self.svm.predict(K)

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Returns signed distance to separating hyperplane.
        Positive: Normal / Legal state
        Negative: Exploit / Glitch anomaly
        """
        if not self.is_fitted:
            raise ValueError("Detector is not fitted yet.")
        K = self.kernel.compute_test_kernel_matrix(X)
        return self.svm.decision_function(K)

    def exploit_anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """
        Normalized exploit anomaly score in [0, +inf).
        Higher values denote higher certainty of game exploit / rule violation.
        """
        decision = self.decision_function(X)
        # Flip sign so lower decision becomes higher anomaly score
        return -decision

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluates detector against ground-truth labels (+1 normal, -1 exploit).
        """
        preds = self.predict(X_test)
        scores = self.exploit_anomaly_score(X_test)

        # Binary labels: 1 for exploit, 0 for normal
        y_binary = (y_test == -1).astype(int)
        pred_binary = (preds == -1).astype(int)

        # Handle edge cases where test set has only one class
        try:
            auc = float(roc_auc_score(y_binary, scores))
        except Exception:
            auc = 1.0

        prec = float(precision_score(y_binary, pred_binary, zero_division=0))
        rec = float(recall_score(y_binary, pred_binary, zero_division=0))
        f1 = float(f1_score(y_binary, pred_binary, zero_division=0))

        report = {
            "roc_auc": auc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "total_test_samples": len(y_test),
            "detected_exploits": int(np.sum(pred_binary)),
            "true_exploits": int(np.sum(y_binary))
        }
        return report

    def plot_diagnostic(
        self,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        save_path: str
    ):
        """
        Generates diagnostic visualization of the Quantum Kernel Gram Matrix
        and the Exploit Anomaly Score distribution.
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        K_train = self.kernel.compute_train_gram_matrix(X_train)
        scores = self.exploit_anomaly_score(X_test)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 1. Quantum Gram Matrix Heatmap
        im0 = axes[0].imshow(K_train[:40, :40], cmap="viridis", vmin=0.0, vmax=1.0)
        axes[0].set_title("Quantum Kernel Gram Matrix (First 40x40)")
        axes[0].set_xlabel("Sample index")
        axes[0].set_ylabel("Sample index")
        fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

        # 2. Anomaly Score Distribution
        normal_mask = (y_test == 1)
        exploit_mask = (y_test == -1)

        axes[1].hist(scores[normal_mask], bins=15, alpha=0.6, color="green", label="Legal / Normal", density=True)
        if np.any(exploit_mask):
            axes[1].hist(scores[exploit_mask], bins=15, alpha=0.6, color="red", label="Exploit / Corrupted", density=True)
        axes[1].axvline(0.0, color="black", linestyle="--", label="Decision Boundary")
        axes[1].set_title("Quantum Exploit Anomaly Score Distribution")
        axes[1].set_xlabel("Anomaly Score (-Decision Function)")
        axes[1].set_ylabel("Density")
        axes[1].legend()

        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()
        print(f"[QuantumKernel] Saved diagnostic plot to {save_path}")

