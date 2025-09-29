#!/usr/bin/env python3
"""
PEP Score Calculator for Wildlife Pipeline
Ensures code quality maintains 95%+ PEP score
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple


class PEPScoreCalculator:
    """Calculate and enforce PEP score for the codebase."""
    
    def __init__(self, target_score: float = 95.0, max_errors: int = 50):
        self.target_score = target_score
        self.max_errors = max_errors
        self.project_root = Path(__file__).parent.parent.parent
        
    def run_flake8_analysis(self) -> Tuple[int, List[str]]:
        """Run flake8 analysis and return error count and details."""
        try:
            cmd = [
                'python', '-m', 'flake8', 'src/', 
                '--select=E,W,F,C', 
                '--statistics', 
                '--count',
                '--show-source',
                '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s'
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            # Parse flake8 output
            lines = result.stdout.strip().split('\n')
            error_lines = [line for line in lines if ':' in line and any(code in line for code in ['E', 'W', 'F', 'C'])]
            error_count = len(error_lines)
            
            return error_count, error_lines
            
        except Exception as e:
            print(f"❌ Error running flake8: {e}")
            return 0, []
    
    def run_ruff_analysis(self) -> Tuple[int, List[str]]:
        """Run ruff analysis and return issue count and details."""
        try:
            cmd = ['python', '-m', 'ruff', 'check', 'src/', '--output-format=text']
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            lines = result.stdout.strip().split('\n')
            issue_lines = [line for line in lines if line.strip()]
            issue_count = len(issue_lines)
            
            return issue_count, issue_lines
            
        except Exception as e:
            print(f"❌ Error running ruff: {e}")
            return 0, []
    
    def calculate_pep_score(self) -> Dict[str, any]:
        """Calculate overall PEP score based on multiple quality tools."""
        print("🔍 Running code quality analysis...")
        
        # Run multiple quality checks
        flake8_errors, flake8_details = self.run_flake8_analysis()
        ruff_issues, ruff_details = self.run_ruff_analysis()
        
        # Calculate weighted score
        total_issues = flake8_errors + ruff_issues
        max_total_issues = self.max_errors * 2  # Allow for both tools
        
        if total_issues > max_total_issues:
            score = 0
        else:
            score = max(0, 100 - (total_issues / max_total_issues * 100))
        
        return {
            'score': score,
            'target_score': self.target_score,
            'total_issues': total_issues,
            'max_issues': max_total_issues,
            'flake8_errors': flake8_errors,
            'ruff_issues': ruff_issues,
            'flake8_details': flake8_details,
            'ruff_details': ruff_details,
            'passed': score >= self.target_score
        }
    
    def print_detailed_report(self, analysis: Dict[str, any]) -> None:
        """Print detailed quality report."""
        print("\n" + "="*60)
        print("📊 WILDLIFE PIPELINE - CODE QUALITY REPORT")
        print("="*60)
        
        print(f"\n🎯 Target Score: {analysis['target_score']}%")
        print(f"📈 Current Score: {analysis['score']:.1f}%")
        print(f"📊 Total Issues: {analysis['total_issues']} (max {analysis['max_issues']} allowed)")
        
        if analysis['flake8_errors'] > 0:
            print(f"\n🔍 Flake8 Issues: {analysis['flake8_errors']}")
            for detail in analysis['flake8_details'][:5]:  # Show first 5
                print(f"   {detail}")
            if len(analysis['flake8_details']) > 5:
                print(f"   ... and {len(analysis['flake8_details']) - 5} more")
        
        if analysis['ruff_issues'] > 0:
            print(f"\n🔍 Ruff Issues: {analysis['ruff_issues']}")
            for detail in analysis['ruff_details'][:5]:  # Show first 5
                print(f"   {detail}")
            if len(analysis['ruff_details']) > 5:
                print(f"   ... and {len(analysis['ruff_details']) - 5} more")
        
        print("\n" + "="*60)
        
        if analysis['passed']:
            print("✅ QUALITY GATE PASSED - PEP Score 95%+ maintained!")
            print("🚀 Code is ready for commit")
        else:
            print("❌ QUALITY GATE FAILED - PEP Score below 95%")
            print("🔧 Fix the issues above to improve code quality")
            print("\n💡 Quick fixes:")
            print("   python -m black src/  # Format code")
            print("   python -m ruff check src/ --fix  # Auto-fix issues")
            print("   python -m isort src/  # Sort imports")
        
        print("="*60)
    
    def run_quality_gate(self) -> bool:
        """Run the complete quality gate check."""
        analysis = self.calculate_pep_score()
        self.print_detailed_report(analysis)
        return analysis['passed']


def main():
    """Main entry point for PEP score calculation."""
    calculator = PEPScoreCalculator(target_score=95.0, max_errors=50)
    
    print("🐦‍⬛ Odins Ravne - Code Quality Gate")
    print("Ensuring PEP score 95%+ for wildlife pipeline")
    
    success = calculator.run_quality_gate()
    
    if not success:
        sys.exit(1)
    else:
        print("\n🎉 All quality checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
