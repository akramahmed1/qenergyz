#!/usr/bin/env python3
"""
Qenergyz Test Report Generator
Consolidates test results from multiple testing categories into comprehensive reports.
"""
import os
import sys
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import argparse


class TestReportGenerator:
    """Generate consolidated test reports from multiple test categories"""
    
    def __init__(self, report_dir: str):
        self.report_dir = Path(report_dir)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.results = {}
        
    def parse_junit_xml(self, xml_file: Path) -> Dict[str, Any]:
        """Parse JUnit XML test results"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Handle both testsuites and testsuite as root element
            if root.tag == "testsuites":
                testsuite = root.find("testsuite")
                if testsuite is not None:
                    suite_elem = testsuite
                else:
                    suite_elem = root
            else:
                suite_elem = root
            
            result = {
                "name": xml_file.stem,
                "tests": int(suite_elem.get("tests", 0)),
                "failures": int(suite_elem.get("failures", 0)),
                "errors": int(suite_elem.get("errors", 0)),
                "skipped": int(suite_elem.get("skipped", 0)),
                "time": float(suite_elem.get("time", 0.0)),
                "success_rate": 0.0,
                "test_cases": []
            }
            
            # Calculate success rate
            total_tests = result["tests"]
            failed_tests = result["failures"] + result["errors"]
            if total_tests > 0:
                result["success_rate"] = ((total_tests - failed_tests) / total_tests) * 100
            
            # Parse individual test cases
            for testcase in suite_elem.findall(".//testcase"):
                test_case = {
                    "name": testcase.get("name"),
                    "classname": testcase.get("classname"),
                    "time": float(testcase.get("time", 0.0)),
                    "status": "passed"
                }
                
                # Check for failures or errors
                if testcase.find("failure") is not None:
                    test_case["status"] = "failed"
                    test_case["failure_message"] = testcase.find("failure").text
                elif testcase.find("error") is not None:
                    test_case["status"] = "error"
                    test_case["error_message"] = testcase.find("error").text
                elif testcase.find("skipped") is not None:
                    test_case["status"] = "skipped"
                    test_case["skip_reason"] = testcase.find("skipped").get("message", "")
                
                result["test_cases"].append(test_case)
            
            return result
            
        except Exception as e:
            print(f"Error parsing {xml_file}: {e}")
            return {
                "name": xml_file.stem,
                "tests": 0,
                "failures": 1,
                "errors": 0,
                "skipped": 0,
                "time": 0.0,
                "success_rate": 0.0,
                "test_cases": [],
                "parse_error": str(e)
            }
    
    def parse_log_file(self, log_file: Path) -> Dict[str, Any]:
        """Parse log file for additional information"""
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
            return {
                "file": log_file.name,
                "size": len(content),
                "lines": len(content.splitlines()),
                "errors": content.count("ERROR"),
                "warnings": content.count("WARNING"),
                "content": content[-1000:]  # Last 1000 characters
            }
        except Exception as e:
            return {
                "file": log_file.name,
                "error": str(e)
            }
    
    def collect_test_results(self):
        """Collect test results from all categories"""
        print(f"Collecting test results from: {self.report_dir}")
        
        # Find all XML result files
        xml_files = list(self.report_dir.glob("*.xml"))
        log_files = list(self.report_dir.glob("*.log"))
        
        print(f"Found {len(xml_files)} XML files and {len(log_files)} log files")
        
        # Parse XML results
        for xml_file in xml_files:
            category_name = xml_file.stem
            result = self.parse_junit_xml(xml_file)
            self.results[category_name] = result
            print(f"Parsed {category_name}: {result['tests']} tests, {result['success_rate']:.1f}% success")
        
        # Parse log files
        self.logs = {}
        for log_file in log_files:
            log_data = self.parse_log_file(log_file)
            self.logs[log_file.stem] = log_data
    
    def calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate overall summary statistics"""
        total_tests = sum(r.get("tests", 0) for r in self.results.values())
        total_failures = sum(r.get("failures", 0) for r in self.results.values())
        total_errors = sum(r.get("errors", 0) for r in self.results.values())
        total_skipped = sum(r.get("skipped", 0) for r in self.results.values())
        total_time = sum(r.get("time", 0.0) for r in self.results.values())
        
        passed_tests = total_tests - total_failures - total_errors
        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_categories": len(self.results),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_failures,
            "error_tests": total_errors,
            "skipped_tests": total_skipped,
            "total_execution_time": total_time,
            "overall_success_rate": overall_success_rate,
            "categories_passed": sum(1 for r in self.results.values() if r.get("success_rate", 0) == 100),
            "categories_failed": sum(1 for r in self.results.values() if r.get("success_rate", 0) < 100)
        }
    
    def generate_html_report(self):
        """Generate HTML report"""
        summary = self.calculate_summary_stats()
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Qenergyz Comprehensive Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background-color: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .category {{ background-color: white; margin: 10px 0; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .success {{ border-left: 4px solid #27ae60; }}
        .partial {{ border-left: 4px solid #f39c12; }}
        .failed {{ border-left: 4px solid #e74c3c; }}
        .stats {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
        .stat {{ text-align: center; padding: 10px; }}
        .progress-bar {{ width: 100%; background-color: #ecf0f1; border-radius: 3px; overflow: hidden; }}
        .progress-fill {{ height: 20px; background-color: #27ae60; transition: width 0.3s; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f8f9fa; }}
        .metric {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .label {{ color: #7f8c8d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Qenergyz Comprehensive Test Report</h1>
        <p>Generated on: {self.timestamp}</p>
        <p>Report Directory: {self.report_dir}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Executive Summary</h2>
        <div class="stats">
            <div class="stat">
                <div class="metric">{summary['total_tests']}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="stat">
                <div class="metric" style="color: #27ae60;">{summary['passed_tests']}</div>
                <div class="label">Passed</div>
            </div>
            <div class="stat">
                <div class="metric" style="color: #e74c3c;">{summary['failed_tests'] + summary['error_tests']}</div>
                <div class="label">Failed/Error</div>
            </div>
            <div class="stat">
                <div class="metric" style="color: #f39c12;">{summary['skipped_tests']}</div>
                <div class="label">Skipped</div>
            </div>
            <div class="stat">
                <div class="metric">{summary['overall_success_rate']:.1f}%</div>
                <div class="label">Success Rate</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {summary['overall_success_rate']}%;"></div>
        </div>
        
        <p><strong>Execution Time:</strong> {summary['total_execution_time']:.2f} seconds</p>
        <p><strong>Categories:</strong> {summary['categories_passed']} passed, {summary['categories_failed']} failed out of {summary['total_categories']} total</p>
    </div>
    
    <div class="summary">
        <h2>📋 Test Categories</h2>
        """
        
        # Add category details
        for category_name, result in sorted(self.results.items()):
            success_rate = result.get("success_rate", 0)
            css_class = "success" if success_rate == 100 else "partial" if success_rate > 0 else "failed"
            
            html_content += f"""
        <div class="category {css_class}">
            <h3>{category_name.replace('_', ' ').title()}</h3>
            <p><strong>Tests:</strong> {result['tests']} | 
               <strong>Passed:</strong> {result['tests'] - result['failures'] - result['errors']} | 
               <strong>Failed:</strong> {result['failures']} | 
               <strong>Errors:</strong> {result['errors']} | 
               <strong>Success Rate:</strong> {success_rate:.1f}%</p>
            <p><strong>Execution Time:</strong> {result['time']:.2f} seconds</p>
            
            """
            
            if result.get("test_cases"):
                html_content += """
            <details>
                <summary>Test Case Details</summary>
                <table>
                    <tr><th>Test Case</th><th>Status</th><th>Time (s)</th><th>Details</th></tr>
                """
                
                for test_case in result["test_cases"]:
                    status_color = {"passed": "#27ae60", "failed": "#e74c3c", "error": "#e74c3c", "skipped": "#f39c12"}.get(test_case["status"], "#000")
                    details = test_case.get("failure_message", test_case.get("error_message", test_case.get("skip_reason", "")))
                    
                    html_content += f"""
                    <tr>
                        <td>{test_case['name']}</td>
                        <td style="color: {status_color}; font-weight: bold;">{test_case['status'].upper()}</td>
                        <td>{test_case['time']:.3f}</td>
                        <td>{details[:100]}{'...' if len(details) > 100 else ''}</td>
                    </tr>
                    """
                
                html_content += """
                </table>
            </details>
                """
            
            html_content += """
        </div>
            """
        
        html_content += """
    </div>
    
    <div class="summary">
        <h2>🏆 Recommendations</h2>
        <ul>
        """
        
        # Add recommendations based on results
        if summary['overall_success_rate'] >= 95:
            html_content += "<li>✅ Excellent test coverage and success rate. Ready for deployment.</li>"
        elif summary['overall_success_rate'] >= 85:
            html_content += "<li>⚠️ Good test coverage with some issues to address before deployment.</li>"
        else:
            html_content += "<li>❌ Critical issues found. Address failing tests before proceeding.</li>"
        
        if summary['categories_failed'] > 0:
            html_content += f"<li>📝 {summary['categories_failed']} test categories need attention.</li>"
        
        if summary['skipped_tests'] > 0:
            html_content += f"<li>🔍 {summary['skipped_tests']} tests were skipped - review if they should be executed.</li>"
        
        html_content += """
        </ul>
    </div>
    
    <div class="summary">
        <h2>📁 Files and Logs</h2>
        <p>Detailed logs and additional information can be found in:</p>
        <ul>
        """
        
        for log_name, log_data in self.logs.items():
            if "error" not in log_data:
                html_content += f"<li><strong>{log_name}.log</strong> - {log_data['lines']} lines, {log_data['errors']} errors, {log_data['warnings']} warnings</li>"
        
        html_content += """
        </ul>
    </div>
    
</body>
</html>
        """
        
        # Write HTML report
        html_file = self.report_dir / "consolidated_report.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated: {html_file}")
        return html_file
    
    def generate_json_report(self):
        """Generate JSON report for programmatic access"""
        summary = self.calculate_summary_stats()
        
        report_data = {
            "metadata": {
                "generated_at": self.timestamp,
                "report_directory": str(self.report_dir),
                "generator_version": "1.0.0"
            },
            "summary": summary,
            "categories": self.results,
            "logs": self.logs
        }
        
        json_file = self.report_dir / "consolidated_report.json"
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"JSON report generated: {json_file}")
        return json_file


def main():
    parser = argparse.ArgumentParser(description="Generate consolidated test reports")
    parser.add_argument("report_dir", help="Directory containing test results")
    parser.add_argument("--format", choices=["html", "json", "both"], default="both",
                       help="Report format to generate")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.report_dir):
        print(f"Error: Report directory '{args.report_dir}' does not exist")
        sys.exit(1)
    
    generator = TestReportGenerator(args.report_dir)
    generator.collect_test_results()
    
    if args.format in ["html", "both"]:
        generator.generate_html_report()
    
    if args.format in ["json", "both"]:
        generator.generate_json_report()
    
    print(f"\n📊 Report generation completed!")
    print(f"Summary: {generator.calculate_summary_stats()}")


if __name__ == "__main__":
    main()