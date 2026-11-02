"""
Hybrid Quantum Reinforcement Learning Policy Engine.
Combines a Classical Linear Pre-Encoder, EstimatorQNN Parameterized Quantum Circuit,
and Trainable Output Scaling Head for Game Exploit & Glitch Hunting.

Compute Optimization:
Enforces a 4-qubit cap and batched episodic Actor-Critic updates with
analytical Estimator gradients to operate strictly within 4-day local compute budgets.
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from torch.utils.tensorboard import SummaryWriter

from qiskit.circuit import ParameterVector, QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_machine_learning.connectors import TorchConnector
from qiskit_machine_learning.neural_networks import EstimatorQNN


def build_estimator_qnn(
    num_qubits: int = 4,
    reps: int = 2
) -> EstimatorQNN:
    """
    Constructs a 4-qubit Parameterized Quantum Circuit (PQC) with:
      - AngleEmbedding inputs: Ry(x_i)
      - Variational layers: Entangling CNOT ladder + Ry(w) + Rz(w)
      - Pauli-Z observables on each qubit to measure <Z_i> in [-1, 1].
    """
    qc = QuantumCircuit(num_qubits)
    input_params = ParameterVector("x", num_qubits)
    weight_params = ParameterVector("w", num_qubits * 2 * reps)

    # 1. State preparation / Angle Encoding
    for i in range(num_qubits):
        qc.ry(input_params[i], i)

    # 2. Variational Entangling Layers
    w_idx = 0
    for r in range(reps):
        # Linear entangling ladder
        for i in range(num_qubits - 1):
            qc.cx(i, i + 1)
        # Parameterized rotations
        for i in range(num_qubits):
            qc.ry(weight_params[w_idx], i)
            qc.rz(weight_params[w_idx + 1], i)
            w_idx += 2

    # 3. Observables: Pauli Z on each qubit
    observables = []
    for i in range(num_qubits):
        pauli_str = "I" * i + "Z" + "I" * (num_qubits - 1 - i)
        observables.append(SparsePauliOp.from_list([(pauli_str, 1.0)]))

    qnn = EstimatorQNN(
        circuit=qc,
        observables=observables,
        input_params=input_params,
        weight_params=weight_params,
        input_gradients=True
    )
    return qnn


class HybridQuantumPolicyNetwork(nn.Module):
    """
    Hybrid Quantum-Classical Actor-Critic Policy Network:
      1. Classical Input Pre-Encoder: Linear(obs_dim, num_qubits) + Tanh * pi
      2. EstimatorQNN Variational Circuit: outputs <Z_i> in [-1, 1]
      3. Output Scaling:
         - Action Policy Head: Linear(num_qubits, action_dim) -> Softmax logits
         - Value Baseline Head: Linear(num_qubits, 1) -> V(s)
    """

    def __init__(
        self,
        obs_dim: int = 4,
        action_dim: int = 5,
        num_qubits: int = 4,
        vqc_reps: int = 2
    ):
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.num_qubits = num_qubits

        # 1. Classical input pre-encoder
        self.encoder = nn.Sequential(
            nn.Linear(obs_dim, num_qubits),
            nn.Tanh()
        )

        # 2. Quantum Estimator QNN Layer
        qnn = build_estimator_qnn(num_qubits=num_qubits, reps=vqc_reps)
        self.q_layer = TorchConnector(qnn)

        # 3. Output Scaling heads
        self.action_head = nn.Linear(num_qubits, action_dim)
        self.value_head = nn.Linear(num_qubits, 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass returning (action_logits, state_value, quantum_expectations).
        """
        # Ensure batch dimension
        if x.dim() == 1:
            x = x.unsqueeze(0)

        # Pre-encoder to [-pi, pi]
        theta = self.encoder(x) * np.pi

        # Quantum expectation values in [-1, 1]^4
        q_out = self.q_layer(theta)

        # Output scaling
        action_logits = self.action_head(q_out)
        state_value = self.value_head(q_out)

        return action_logits, state_value, q_out

    def get_action(self, obs: np.ndarray) -> Tuple[int, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Samples an action from the policy given a numpy observation.
        Returns: (action_idx, log_prob, state_value, quantum_expectations)
        """
        device = next(self.parameters()).device
        obs_tensor = torch.as_tensor(obs, dtype=torch.float32, device=device)
        logits, val, q_out = self.forward(obs_tensor)
        dist = Categorical(logits=logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        return action.item(), log_prob, val.squeeze(-1), q_out.squeeze(0)


class QuantumExploitHunterAgent:
    """
    Quantum RL Exploit Hunter Agent.
    Optimizes the Hybrid Quantum-Classical Policy using Actor-Critic with
    Intrinsic Exploit Curiosity Bonus to actively seek out game glitches.
    """

    def __init__(
        self,
        obs_dim: int = 4,
        action_dim: int = 5,
        num_qubits: int = 4,
        vqc_reps: int = 1,
        lr: float = 0.001,
        gamma: float = 0.99,
        entropy_coef: float = 0.01,
        value_loss_coef: float = 0.5,
        exploit_bonus_weight: float = 2.0,
        device: str = "cpu"
    ):
        self.device = torch.device(device)
        self.gamma = gamma
        self.entropy_coef = entropy_coef
        self.value_loss_coef = value_loss_coef
        self.exploit_bonus_weight = exploit_bonus_weight

        self.policy = HybridQuantumPolicyNetwork(
            obs_dim=obs_dim,
            action_dim=action_dim,
            num_qubits=num_qubits,
            vqc_reps=vqc_reps
        ).to(self.device)

        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)

    def train_on_environment(
        self,
        env: Any,
        num_episodes: int = 30,
        max_steps_per_episode: int = 60,
        anomaly_detector: Optional[Any] = None,
        log_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the QRL exploit hunting training loop.
        Logs rewards, exploit discoveries, and quantum observables.
        """
        writer = SummaryWriter(log_dir) if log_dir else None
        episode_rewards: List[float] = []
        episode_lengths: List[int] = []
        exploit_discoveries: List[int] = []

        total_glitches_found = 0
        t0 = time.time()

        print(f"[QRLAgent] Starting Hybrid QRL Exploit Training for {num_episodes} episodes...")

        for ep in range(1, num_episodes + 1):
            obs, info = env.reset()
            ep_reward = 0.0
            ep_glitches = 0
            
            log_probs = []
            values = []
            rewards = []
            entropy_list = []

            for step in range(max_steps_per_episode):
                action, log_prob, val, q_feat = self.policy.get_action(obs)
                next_obs, env_reward, term, trunc, info = env.step(action)

                # Exploit Curiosity Shaping:
                # If an anomaly detector is provided or the environment flags a glitch, add intrinsic bonus
                intrinsic_bonus = 0.0
                if anomaly_detector is not None:
                    # Score anomaly from quantum kernel
                    anom_score = float(anomaly_detector.exploit_anomaly_score(np.array([next_obs]))[0])
                    if anom_score > 0.0:
                        intrinsic_bonus = anom_score * self.exploit_bonus_weight
                elif info.get("glitch_triggered", False):
                    intrinsic_bonus = self.exploit_bonus_weight * 5.0

                if info.get("glitch_triggered", False):
                    ep_glitches += 1
                    total_glitches_found += 1

                total_step_reward = env_reward + intrinsic_bonus

                log_probs.append(log_prob)
                values.append(val)
                rewards.append(total_step_reward)
                ep_reward += total_step_reward

                obs = next_obs
                if term or trunc:
                    break

            # Compute discounted returns and advantages
            returns = []
            G = 0.0
            for r in reversed(rewards):
                G = r + self.gamma * G
                returns.insert(0, G)
            returns = torch.tensor(returns, dtype=torch.float32, device=self.device)

            if len(returns) > 1:
                returns = (returns - returns.mean()) / (returns.std() + 1e-8)

            policy_losses = []
            value_losses = []
            for lp, val, ret in zip(log_probs, values, returns):
                advantage = ret - val.item()
                policy_losses.append(-lp * advantage)
                value_losses.append(nn.functional.mse_loss(val.view(-1), ret.view(-1)))

            if policy_losses:
                total_loss = torch.stack(policy_losses).sum() + self.value_loss_coef * torch.stack(value_losses).sum()
                self.optimizer.zero_grad()
                total_loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), max_norm=1.0)
                self.optimizer.step()

            episode_rewards.append(ep_reward)
            episode_lengths.append(len(rewards))
            exploit_discoveries.append(ep_glitches)

            if writer:
                writer.add_scalar("QRL/Episode_Reward", ep_reward, ep)
                writer.add_scalar("QRL/Episode_Length", len(rewards), ep)
                writer.add_scalar("QRL/Exploits_Discovered", ep_glitches, ep)

            if ep % 5 == 0 or ep == num_episodes:
                avg_rew = np.mean(episode_rewards[-5:])
                print(f"[QRLAgent] Ep {ep:02d}/{num_episodes} | Avg Reward: {avg_rew:+.2f} | Exploits Found: {ep_glitches} (Total: {total_glitches_found})")

        if writer:
            writer.close()

        elapsed = time.time() - t0
        return {
            "episode_rewards": episode_rewards,
            "episode_lengths": episode_lengths,
            "exploit_discoveries": exploit_discoveries,
            "total_glitches_found": total_glitches_found,
            "training_time_seconds": elapsed
        }

    def save_checkpoint(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.policy.state_dict(), path)
        print(f"[QRLAgent] Saved policy weights to {path}")

    def load_checkpoint(self, path: str):
        self.policy.load_state_dict(torch.load(path, map_location=self.device))
        print(f"[QRLAgent] Loaded policy weights from {path}")

    def plot_training_metrics(self, metrics: Dict[str, Any], save_path: str):
        """Generates training diagnostic figure showing reward curves and exploit discovery count."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        rewards = metrics["episode_rewards"]
        exploits = metrics["exploit_discoveries"]
        episodes = list(range(1, len(rewards) + 1))

        fig, ax1 = plt.subplots(figsize=(10, 5))

        color = "tab:blue"
        ax1.set_xlabel("Episode")
        ax1.set_ylabel("Total Return (Env + Exploit Curiosity)", color=color)
        ax1.plot(episodes, rewards, color=color, linewidth=2, label="Reward")
        ax1.tick_params(axis="y", labelcolor=color)

        ax2 = ax1.twinx()
        color = "tab:red"
        ax2.set_ylabel("Glitches / Exploits Discovered", color=color)
        ax2.bar(episodes, exploits, color=color, alpha=0.35, label="Exploits")
        ax2.tick_params(axis="y", labelcolor=color)

        plt.title(f"Quantum RL Exploit Discovery Training (Total Glitches: {metrics['total_glitches_found']})")
        fig.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()
        print(f"[QRLAgent] Saved training plot to {save_path}")
