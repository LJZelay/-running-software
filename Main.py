"""
CSE 4504 Team Project - Main Application
Main entry point that integrates all features
"""

import sys
from typing import Dict, Any
from datetime import datetime
import traceback

# Import feature modules
from Feature1 import Feature1
from Feature2 import Feature2  # Placeholder for future features
from Utils import logger, validate_input, format_output


class CSE4504Project:
    """
    Main application class that integrates all features
    Follows the GitHub workflow: features are developed independently and integrated here
    """
    
    def __init__(self):
        """Initialize the application with all available features"""
        self.features = {
            'feature1': Feature1(),
            'feature2': Feature2(),  # Will be implemented in future sprints
        }
        self.feature_history = []  # Track feature usage
        
    def list_features(self) -> Dict[str, str]:
        """List all available features with descriptions"""
        return {
            'feature1': 'Text Analysis and Processing',
            'feature2': 'Data Visualization (Coming Soon)',
        }
    
    def run_feature(self, feature_name: str, *args, **kwargs) -> Any:
        """
        Execute a specific feature with the provided arguments
        
        Args:
            feature_name: Name of the feature to run
            *args: Positional arguments for the feature
            **kwargs: Keyword arguments for the feature
            
        Returns:
            Feature execution result
            
        Raises:
            ValueError: If feature doesn't exist
            Exception: Any exception from feature execution
        """
        if feature_name not in self.features:
            available = ', '.join(self.features.keys())
            raise ValueError(f"Feature '{feature_name}' not found. Available: {available}")
        
        try:
            # Log feature execution
            logger.info(f"Executing feature: {feature_name}")
            
            # Execute the feature
            result = self.features[feature_name].execute(*args, **kwargs)
            
            # Record in history
            self.feature_history.append({
                'timestamp': datetime.now(),
                'feature': feature_name,
                'args': args,
                'kwargs': kwargs,
                'success': True
            })
            
            return result
            
        except Exception as e:
            # Record failure
            self.feature_history.append({
                'timestamp': datetime.now(),
                'feature': feature_name,
                'args': args,
                'kwargs': kwargs,
                'success': False,
                'error': str(e)
            })
            
            logger.error(f"Feature '{feature_name}' failed: {str(e)}")
            raise
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get statistics about feature usage"""
        if not self.feature_history:
            return {"total_executions": 0, "success_rate": 100.0}
        
        total = len(self.feature_history)
        successful = sum(1 for h in self.feature_history if h['success'])
        success_rate = (successful / total) * 100
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": total - successful,
            "success_rate": round(success_rate, 2),
            "features_used": list(set(h['feature'] for h in self.feature_history))
        }
    
    def interactive_mode(self):
        """Run the application in interactive mode"""
        print("=" * 50)
        print("CSE 4504 Team Project - Interactive Mode")
        print("=" * 50)
        
        while True:
            print("\nAvailable Features:")
            features = self.list_features()
            for idx, (name, desc) in enumerate(features.items(), 1):
                print(f"  {idx}. {name}: {desc}")
            
            print("\nCommands:")
            print("  run <feature_name> [args] - Run a feature")
            print("  stats                     - Show usage statistics")
            print("  history                   - Show execution history")
            print("  help                      - Show this help")
            print("  exit                      - Exit the application")
            
            try:
                command = input("\n>>> ").strip().split()
                
                if not command:
                    continue
                    
                cmd = command[0].lower()
                
                if cmd == 'exit':
                    print("Thank you for using CSE 4504 Project!")
                    break
                    
                elif cmd == 'stats':
                    stats = self.get_usage_statistics()
                    print("\nUsage Statistics:")
                    for key, value in stats.items():
                        print(f"  {key}: {value}")
                        
                elif cmd == 'history':
                    if not self.feature_history:
                        print("No execution history yet.")
                    else:
                        print("\nExecution History:")
                        for i, h in enumerate(self.feature_history[-5:], 1):  # Last 5
                            status = "✓" if h['success'] else "✗"
                            print(f"  {i}. [{status}] {h['feature']} at {h['timestamp'].strftime('%H:%M:%S')}")
                            
                elif cmd == 'help':
                    continue  # Will show help again at next iteration
                    
                elif cmd == 'run':
                    if len(command) < 2:
                        print("Usage: run <feature_name> [args]")
                        continue
                    
                    feature_name = command[1]
                    args = command[2:] if len(command) > 2 else []
                    
                    try:
                        result = self.run_feature(feature_name, *args)
                        print(f"\nResult: {result}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"Feature execution failed: {e}")
                        if input("Show traceback? (y/n): ").lower() == 'y':
                            traceback.print_exc()
                            
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'exit' to quit.")
            except EOFError:
                print("\n\nExiting...")
                break


def main():
    """Main entry point"""
    # Initialize the application
    app = CSE4504Project()
    
    # Check if command line arguments were provided
    if len(sys.argv) > 1:
        # Command-line mode
        if sys.argv[1] == 'interactive':
            app.interactive_mode()
        elif sys.argv[1] == 'run' and len(sys.argv) > 2:
            feature_name = sys.argv[2]
            args = sys.argv[3:] if len(sys.argv) > 3 else []
            try:
                result = app.run_feature(feature_name, *args)
                print(result)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[1] == 'stats':
            stats = app.get_usage_statistics()
            for key, value in stats.items():
                print(f"{key}: {value}")
        else:
            print(f"Usage: python main.py [interactive|run <feature> [args]|stats]")
            print("  interactive  - Launch interactive mode")
            print("  run <feature> [args] - Run a specific feature")
            print("  stats        - Show usage statistics")
            sys.exit(1)
    else:
        # Default to interactive mode
        app.interactive_mode()


if __name__ == "__main__":
    main()