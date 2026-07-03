"""
Main entry point for the Meta-Agent Math Debate System
Initializes the system and provides CLI interface
"""

import argparse
import sys
import os
from typing import Dict, Any
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.meta_agent import MetaAgent
from utils.data_processor import DataProcessor
from utils.logger import setup_logger
from config import API_INSTRUCTIONS

logger = setup_logger(__name__)

class MathDebateSystemCLI:
    """Command Line Interface for the Math Debate System"""
    
    def __init__(self):
        self.meta_agent = None
        self.data_processor = DataProcessor()
    
    def initialize(self):
        """Initialize the system"""
        logger.info("Initializing Meta-Agent Math Debate System...")
        
        try:
            # Create necessary directories
            os.makedirs("database", exist_ok=True)
            os.makedirs("logs", exist_ok=True)
            os.makedirs("models", exist_ok=True)
            os.makedirs("utils", exist_ok=True)
            os.makedirs("agents", exist_ok=True)
            os.makedirs("rag", exist_ok=True)
            
            # Initialize meta-agent
            self.meta_agent = MetaAgent()
            self.meta_agent.initialize()
            
            # Load sample data
            self.data_processor.load_sample_data()
            
            logger.info("System initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {str(e)}")
            return False
    
    def solve_problem(self, problem: str, use_debate: bool = False, rounds: int = 3) -> Dict[str, Any]:
        """Solve a problem using the meta-agent system"""
        if not self.meta_agent:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        logger.info(f"Solving problem: {problem[:100]}...")
        
        if use_debate:
            result = self.meta_agent.run_debate(problem, rounds)
            logger.info(f"Debate completed. Winner: {result.get('debate_winner')}")
            return result
        else:
            result = self.meta_agent.solve_problem(problem)
            logger.info(f"Problem solved by: {result.get('best_agent')}")
            return result
    
    def analyze_problem(self, problem: str) -> Dict[str, Any]:
        """Analyze a problem to get type, hints, etc."""
        if not self.meta_agent:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        patterns = self.meta_agent.retriever_agent.find_solution_patterns(problem)
        hints = self.meta_agent.retriever_agent.get_contextual_hints(problem)
        
        return {
            "analysis": patterns,
            "hints": hints
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self.meta_agent:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        return self.meta_agent.get_stats()
    
    def interactive_mode(self):
        """Run interactive mode for problem solving"""
        print("\n" + "="*60)
        print("Meta-Agent Math Debate System - Interactive Mode")
        print("="*60)
        print("Commands:")
        print(" 'solve <problem>' - Solve a math problem")
        print(" 'debate <problem>' - Solve using agent debate")
        print(" 'analyze <problem>' - Analyze problem type and get hints")
        print(" 'stats' - Show system statistics")
        print(" 'sample' - Show sample problems")
        print(" 'help' - Show this help")
        print(" 'quit' - Exit")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye!")
                    break
                
                elif user_input.lower() in ['help', 'h']:
                    print("\nAvailable commands:")
                    print(" solve <problem> - Solve a math problem")
                    print(" debate <problem> - Use agent debate to solve")
                    print(" analyze <problem> - Analyze problem")
                    print(" stats - System statistics")
                    print(" sample - Sample problems")
                    print(" help - This help")
                    print(" quit - Exit")
                
                elif user_input.lower() == 'stats':
                    stats = self.get_stats()
                    print(f"\nSystem Statistics:")
                    print(f" Total Problems: {stats['vector_store']['total_documents']}")
                    print(f" Active Agents: {stats['agent_count']}")
                    print(f" Memory Usage: {stats['vector_store']['memory_usage_mb']:.1f} MB")
                    print(f" Problem Types: {', '.join(stats['problem_types'].keys())}")
                
                elif user_input.lower() == 'sample':
                    samples = self.data_processor.get_sample_problems()
                    print(f"\nSample Problems ({len(samples)} available):")
                    for i, problem in enumerate(samples[:5], 1):
                        print(f" {i}. {problem['problem'][:80]}...")
                    if len(samples) > 5:
                        print(f" ... and {len(samples) - 5} more")
                
                elif user_input.lower().startswith('solve '):
                    problem = user_input[6:].strip()
                    if problem:
                        result = self.solve_problem(problem)
                        print(f"\nSolution by {result['best_agent']}:")
                        print(f"Answer: {result['answer']}")
                        print(f"Confidence: {result['confidence']*100:.1f}%")
                        print(f"Solution:\n{result['solution']}")
                    else:
                        print("Please provide a problem to solve.")
                
                elif user_input.lower().startswith('debate '):
                    problem = user_input[7:].strip()
                    if problem:
                        result = self.solve_problem(problem, use_debate=True)
                        print(f"\nDebate Winner: {result['debate_winner']}")
                        print(f"Solution: {result['final_solution']}")
                        print(f"Debate Rounds: {result['debate_rounds']}")
                    else:
                        print("Please provide a problem for debate.")
                
                elif user_input.lower().startswith('analyze '):
                    problem = user_input[8:].strip()
                    if problem:
                        result = self.analyze_problem(problem)
                        analysis = result['analysis']
                        hints = result['hints']
                        
                        print(f"\nProblem Analysis:")
                        print(f" Type: {analysis.get('problem_type', 'Unknown')}")
                        print(f" Difficulty: {analysis.get('difficulty', 'Unknown')}")
                        print(f" Key Concepts: {analysis.get('concepts', 'None identified')}")
                        
                        if hints:
                            print(f"\nHints:")
                            for i, hint in enumerate(hints, 1):
                                print(f" {i}. {hint}")
                    else:
                        print("Please provide a problem to analyze.")
                
                else:
                    print(f"Unknown command: {user_input}. Type 'help' for available commands.")
            
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except Exception as e:
                print(f"Error: {str(e)}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Meta-Agent Math Debate System")
    parser.add_argument('--problem', '-p', help='Math problem to solve')
    parser.add_argument('--debate', '-d', action='store_true', help='Use debate mode')
    parser.add_argument('--rounds', '-r', type=int, default=3, help='Number of debate rounds')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analyze problem instead of solving')
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode')
    parser.add_argument('--stats', '-s', action='store_true', help='Show system statistics')
    parser.add_argument('--server', action='store_true', help='Start Flask server')
    
    args = parser.parse_args()
    
    # Initialize system
    cli = MathDebateSystemCLI()
    if not cli.initialize():
        print("Failed to initialize system. Check API keys and configuration.")
        print("\nAPI Key Setup Instructions:")
        print(API_INSTRUCTIONS)
        return 1
    
    try:
        if args.server:
            print("Starting Flask server...")
            from app import app
            app.run(host='0.0.0.0', port=5000, debug=True)
            
        elif args.interactive:
            cli.interactive_mode()
            
        elif args.stats:
            stats = cli.get_stats()
            print(f"System Statistics:")
            print(f" Total Problems: {stats['vector_store']['total_documents']}")
            print(f" Active Agents: {stats['agent_count']}")
            print(f" Memory Usage: {stats['vector_store']['memory_usage_mb']:.1f} MB")
            
        elif args.problem:
            if args.analyze:
                result = cli.analyze_problem(args.problem)
                analysis = result['analysis']
                hints = result['hints']
                
                print(f"Problem Analysis:")
                print(f" Type: {analysis.get('problem_type', 'Unknown')}")
                print(f" Difficulty: {analysis.get('difficulty', 'Unknown')}")
                print(f" Key Concepts: {analysis.get('concepts', 'None')}")
                
                if hints:
                    print(f"\nHints:")
                    for i, hint in enumerate(hints, 1):
                        print(f" {i}. {hint}")
            else:
                result = cli.solve_problem(args.problem, args.debate, args.rounds)
                
                if args.debate:
                    print(f"Debate Winner: {result['debate_winner']}")
                    print(f"Final Solution: {result['final_solution']}")
                    print(f"Confidence: {result.get('confidence', 0)*100:.1f}%")
                else:
                    print(f"Best Agent: {result['best_agent']}")
                    print(f"Answer: {result['answer']}")
                    print(f"Confidence: {result['confidence']*100:.1f}%")
                    print(f"Time: {result['total_time']:.2f}s")
                    print(f"\nSolution:\n{result['solution']}")
        
        else:
            print("No action specified. Use --help for options or --interactive for interactive mode.")
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
    finally:
        if cli.meta_agent:
            cli.meta_agent.cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())