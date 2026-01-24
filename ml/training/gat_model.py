"""
GraphGuard - Graph Attention Network (GAT) Model
==================================================
File: ml/training/gat_model.py
Reference: Specification.md Lines 1625-1705

Goal: Implement Graph Attention Network for fraud detection.

Architecture:
- GATConv(in, hidden, heads=8) → ELU → Dropout
- GATConv(hidden*8, hidden, heads=1) → global_mean_pool
- Linear → LogSoftmax

Gotchas (from spec):
- GAT needs entire graph in memory - use NeighborLoader for large graphs (>1M nodes)
- Multi-head attention increases memory
"""

from typing import Optional, Dict, Any, List

import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv, global_mean_pool
from torch_geometric.data import Data, Dataset
from torch_geometric.loader import DataLoader
import numpy as np
import mlflow
import mlflow.pytorch
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# GAT Model Architecture (Spec Lines 1633-1658)
# ============================================

class FraudGAT(torch.nn.Module):
    """
    Graph Attention Network for fraud detection.
    Reference: Specification.md Lines 1633-1658
    """
    
    def __init__(
        self,
        in_channels: int = 6,
        hidden_channels: int = 128,
        out_channels: int = 2,
        heads: int = 8,
        dropout: float = 0.6
    ):
        super().__init__()
        
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.heads = heads
        self.dropout = dropout
        
        # GAT layers
        self.conv1 = GATConv(
            in_channels, 
            hidden_channels, 
            heads=heads, 
            dropout=dropout
        )
        self.conv2 = GATConv(
            hidden_channels * heads, 
            hidden_channels, 
            heads=1, 
            concat=False, 
            dropout=dropout
        )
        
        # MLP classifier
        self.fc1 = torch.nn.Linear(hidden_channels, hidden_channels // 2)
        self.fc2 = torch.nn.Linear(hidden_channels // 2, out_channels)
    
    def forward(self, data: Data) -> torch.Tensor:
        """
        Forward pass through the network.
        
        Args:
            data: PyG Data object with x, edge_index, and batch
        
        Returns:
            Log-softmax probabilities for each class
        """
        x, edge_index = data.x, data.edge_index
        batch = getattr(data, "batch", None)
        if batch is None:
            # Treat a single graph as one batch when batch info is missing.
            batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)
        
        # GAT layers
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = F.elu(self.conv1(x, edge_index))
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        
        # Graph-level pooling (aggregate node embeddings)
        x = global_mean_pool(x, batch)
        
        # MLP classifier
        x = F.relu(self.fc1(x))
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.fc2(x)
        
        return F.log_softmax(x, dim=1)
    
    def get_node_embeddings(self, data: Data) -> torch.Tensor:
        """Get node embeddings after GAT layers (before pooling)."""
        x, edge_index = data.x, data.edge_index
        
        x = F.elu(self.conv1(x, edge_index))
        x = self.conv2(x, edge_index)
        
        return x


# ============================================
# GAT Trainer Class
# ============================================

class GATTrainer:
    """
    Trainer for Graph Attention Network.
    Reference: Specification.md Lines 1660-1697
    """
    
    def __init__(
        self,
        model: FraudGAT,
        device: Optional[torch.device] = None,
        learning_rate: float = 0.005,
        weight_decay: float = 5e-4
    ):
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = model.to(self.device)
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        logger.info(
            "GAT Trainer initialized",
            device=str(self.device),
            in_channels=model.in_channels,
            hidden_channels=model.hidden_channels
        )
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """
        Train for one epoch.
        Reference: Specification.md Lines 1668-1679
        """
        self.model.train()
        total_loss = 0
        
        for data in train_loader:
            data = data.to(self.device)
            self.optimizer.zero_grad()
            
            out = self.model(data)
            loss = F.nll_loss(out, data.y)
            
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(train_loader)
    
    @torch.no_grad()
    def evaluate(self, loader: DataLoader) -> Dict[str, float]:
        """
        Evaluate model on a dataset.
        Reference: Specification.md Lines 1681-1688
        """
        self.model.eval()
        
        all_preds = []
        all_labels = []
        all_probs = []
        
        for data in loader:
            data = data.to(self.device)
            out = self.model(data)
            
            probs = torch.exp(out)[:, 1]  # Probability of fraud
            pred = out.argmax(dim=1)
            
            all_probs.extend(probs.cpu().numpy())
            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(data.y.cpu().numpy())
        
        all_preds = np.array(all_preds)
        all_labels = np.array(all_labels)
        all_probs = np.array(all_probs)
        
        # Calculate metrics
        accuracy = (all_preds == all_labels).mean()
        
        # Handle potential edge cases
        if len(np.unique(all_labels)) > 1:
            roc_auc = roc_auc_score(all_labels, all_probs)
            precision = precision_score(all_labels, all_preds, zero_division=0)
            recall = recall_score(all_labels, all_preds, zero_division=0)
            f1 = f1_score(all_labels, all_preds, zero_division=0)
        else:
            roc_auc = precision = recall = f1 = 0.0
        
        return {
            'accuracy': accuracy,
            'roc_auc': roc_auc,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }
    
    def train(
        self,
        train_loader: DataLoader,
        test_loader: DataLoader,
        epochs: int = 200,
        log_interval: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Full training loop.
        Reference: Specification.md Lines 1690-1694
        """
        history = []
        
        logger.info("Starting GAT training", epochs=epochs)
        
        for epoch in range(1, epochs + 1):
            loss = self.train_epoch(train_loader)
            
            if epoch % log_interval == 0:
                metrics = self.evaluate(test_loader)
                metrics['epoch'] = epoch
                metrics['train_loss'] = loss
                history.append(metrics)
                
                logger.info(
                    f"Epoch {epoch:03d}",
                    loss=f"{loss:.4f}",
                    accuracy=f"{metrics['accuracy']:.4f}",
                    roc_auc=f"{metrics['roc_auc']:.4f}"
                )
        
        return history
    
    def save(self, path: str) -> None:
        """Save model to disk."""
        torch.save(self.model.state_dict(), path)
        logger.info("Model saved", path=path)
    
    def load(self, path: str) -> None:
        """Load model from disk."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        logger.info("Model loaded", path=path)
    
    def log_to_mlflow(
        self,
        metrics: Dict[str, float],
        experiment_name: str = "fraud_detection",
        run_name: str = "gat_model"
    ) -> str:
        """Log to MLflow."""
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params({
                "model": "gat",
                "in_channels": self.model.in_channels,
                "hidden_channels": self.model.hidden_channels,
                "heads": self.model.heads,
                "dropout": self.model.dropout
            })
            
            mlflow.log_metrics(metrics)
            mlflow.pytorch.log_model(self.model, "model")
            
            return run.info.run_id


# ============================================
# Graph Dataset (Simplified for Local Testing)
# ============================================

class SyntheticFraudGraphDataset(Dataset):
    """
    Synthetic graph dataset for testing (without Neo4j).
    For production, use FraudGraphDataset from Specification.md Lines 1535-1612.
    """
    
    def __init__(
        self,
        num_graphs: int = 1000,
        num_nodes_per_graph: int = 20,
        num_node_features: int = 6,
        fraud_rate: float = 0.1
    ):
        super().__init__()
        
        self.graphs = []
        
        for i in range(num_graphs):
            # Generate random graph
            num_nodes = np.random.randint(10, num_nodes_per_graph)
            num_edges = num_nodes * 2
            
            # Node features (pagerank, betweenness, degree, etc.)
            x = torch.randn(num_nodes, num_node_features)
            
            # Random edges
            edge_index = torch.randint(0, num_nodes, (2, num_edges))
            
            # Random label (fraud or not)
            label = 1 if np.random.random() < fraud_rate else 0
            
            data = Data(
                x=x,
                edge_index=edge_index,
                y=torch.tensor([label], dtype=torch.long)
            )
            
            self.graphs.append(data)
    
    def len(self) -> int:
        return len(self.graphs)
    
    def get(self, idx: int) -> Data:
        return self.graphs[idx]


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train GAT fraud detection model")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--hidden", type=int, default=128, help="Hidden channels")
    parser.add_argument("--heads", type=int, default=8, help="Attention heads")
    parser.add_argument("--output", default="./gat_model.pth", help="Output model path")
    args = parser.parse_args()
    
    # Create synthetic dataset for testing
    print("Creating synthetic dataset for testing...")
    dataset = SyntheticFraudGraphDataset(num_graphs=1000)
    
    # Split dataset
    train_dataset = dataset[:800]
    test_dataset = dataset[800:]
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32)
    
    # Create model and trainer
    model = FraudGAT(
        in_channels=6,
        hidden_channels=args.hidden,
        out_channels=2,
        heads=args.heads
    )
    
    trainer = GATTrainer(model)
    
    # Train
    print(f"\nTraining for {args.epochs} epochs...")
    history = trainer.train(train_loader, test_loader, epochs=args.epochs)
    
    # Final evaluation
    final_metrics = trainer.evaluate(test_loader)
    print(f"\nFinal Results:")
    print(f"  Accuracy: {final_metrics['accuracy']:.4f}")
    print(f"  ROC-AUC: {final_metrics['roc_auc']:.4f}")
    print(f"  F1 Score: {final_metrics['f1_score']:.4f}")
    
    # Save model
    trainer.save(args.output)
    print(f"\nModel saved to {args.output}")
