#!/usr/bin/env python3
"""
Location Sync Tool

This tool synchronizes location labels with Git repository:
- Export location labels to JSON files
- Commit and push changes to Git
- Pull and import location updates from Git
- Handle conflicts and merge issues
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import shutil

from .location_classifier import LocationClassifier, Location


class LocationSync:
    """Tool for synchronizing location labels with Git."""
    
    def __init__(self, db_path: Path, git_repo_path: Path, labels_dir: str = "location_labels"):
        self.classifier = LocationClassifier(db_path)
        self.git_repo_path = git_repo_path
        self.labels_dir = labels_dir
        self.labels_path = git_repo_path / labels_dir
    
    def export_labels(self, output_file: Optional[Path] = None) -> Path:
        """Export location labels to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.labels_path / f"locations_{timestamp}.json"
        
        # Ensure labels directory exists
        self.labels_path.mkdir(parents=True, exist_ok=True)
        
        # Get all locations
        locations = self.classifier.get_locations()
        
        # Create export data
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "exported_by": "location_sync_tool",
            "total_locations": len(locations),
            "locations": [self._location_to_dict(loc) for loc in locations]
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📤 Exported {len(locations)} locations to {output_file}")
        return output_file
    
    def _location_to_dict(self, location: Location) -> Dict:
        """Convert Location object to dictionary."""
        return {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "radius_meters": location.radius_meters,
            "description": location.description,
            "created_at": location.created_at,
            "updated_at": location.updated_at
        }
    
    def import_labels(self, input_file: Path, merge_strategy: str = "skip_existing") -> Tuple[int, int]:
        """Import location labels from JSON file."""
        with open(input_file, 'r') as f:
            import_data = json.load(f)
        
        locations = import_data.get('locations', [])
        imported_count = 0
        skipped_count = 0
        
        # Get existing locations
        existing_locations = {loc.id: loc for loc in self.classifier.get_locations()}
        
        for location_data in locations:
            location_id = location_data.get('id')
            
            if location_id in existing_locations:
                if merge_strategy == "skip_existing":
                    print(f"⏭️  Skipping existing location: {location_data['name']}")
                    skipped_count += 1
                    continue
                elif merge_strategy == "update_existing":
                    # Update existing location
                    location = Location(**location_data)
                    location.updated_at = datetime.now().isoformat()
                    self.classifier.add_location(location)
                    print(f"🔄 Updated location: {location.name}")
                    imported_count += 1
                elif merge_strategy == "create_new":
                    # Create new location with modified ID
                    location = Location(**location_data)
                    location.id = self.classifier._generate_location_id(location.name)
                    self.classifier.add_location(location)
                    print(f"➕ Created new location: {location.name}")
                    imported_count += 1
            else:
                # Create new location
                location = Location(**location_data)
                self.classifier.add_location(location)
                print(f"✅ Imported location: {location.name}")
                imported_count += 1
        
        return imported_count, skipped_count
    
    def commit_and_push(self, message: str = None) -> bool:
        """Commit and push location labels to Git."""
        if message is None:
            message = f"Update location labels - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            # Change to git repository directory
            original_cwd = Path.cwd()
            os.chdir(self.git_repo_path)
            
            # Add all files in labels directory
            subprocess.run(["git", "add", self.labels_dir], check=True)
            
            # Check if there are changes to commit
            result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
            if result.returncode == 0:
                print("📝 No changes to commit")
                return True
            
            # Commit changes
            subprocess.run(["git", "commit", "-m", message], check=True)
            print(f"✅ Committed: {message}")
            
            # Push to remote
            subprocess.run(["git", "push"], check=True)
            print("🚀 Pushed to remote repository")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def pull_and_import(self, merge_strategy: str = "skip_existing") -> Tuple[int, int]:
        """Pull latest changes from Git and import new location labels."""
        try:
            # Change to git repository directory
            original_cwd = Path.cwd()
            os.chdir(self.git_repo_path)
            
            # Pull latest changes
            subprocess.run(["git", "pull"], check=True)
            print("📥 Pulled latest changes from remote")
            
            # Find all location files
            location_files = list(self.labels_path.glob("locations_*.json"))
            
            if not location_files:
                print("📭 No location files found")
                return 0, 0
            
            # Sort by modification time (newest first)
            location_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            total_imported = 0
            total_skipped = 0
            
            # Import from all files
            for location_file in location_files:
                print(f"📥 Importing from {location_file.name}")
                imported, skipped = self.import_labels(location_file, merge_strategy)
                total_imported += imported
                total_skipped += skipped
            
            print(f"📊 Import Summary:")
            print(f"  Imported: {total_imported}")
            print(f"  Skipped: {total_skipped}")
            
            return total_imported, total_skipped
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return 0, 0
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def sync_with_remote(self, merge_strategy: str = "skip_existing") -> bool:
        """Full sync: export, commit, push, pull, import."""
        print("🔄 Starting full sync with remote repository")
        
        # Step 1: Export current labels
        print("\n📤 Step 1: Exporting current labels")
        export_file = self.export_labels()
        
        # Step 2: Commit and push
        print("\n📤 Step 2: Committing and pushing changes")
        if not self.commit_and_push():
            print("❌ Failed to commit and push")
            return False
        
        # Step 3: Pull and import
        print("\n📥 Step 3: Pulling and importing remote changes")
        imported, skipped = self.pull_and_import(merge_strategy)
        
        print(f"\n✅ Sync completed:")
        print(f"  Exported: {export_file.name}")
        print(f"  Imported: {imported}")
        print(f"  Skipped: {skipped}")
        
        return True
    
    def show_status(self) -> None:
        """Show Git status and location statistics."""
        try:
            # Change to git repository directory
            original_cwd = Path.cwd()
            os.chdir(self.git_repo_path)
            
            # Show Git status
            print("📊 Git Status:")
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if result.stdout.strip():
                print(result.stdout)
            else:
                print("  No uncommitted changes")
            
            # Show recent commits
            print("\n📝 Recent Commits:")
            result = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True)
            print(result.stdout)
            
            # Show location statistics
            stats = self.classifier.get_statistics()
            print(f"\n📊 Location Statistics:")
            print(f"  Total locations: {stats['total_locations']}")
            print(f"  Total images: {stats['total_images']}")
            print(f"  Classified: {stats['classified_images']}")
            print(f"  Unknown: {stats['unknown_locations']}")
            print(f"  Classification rate: {stats['classification_rate']:.1%}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    def resolve_conflicts(self) -> bool:
        """Help resolve Git conflicts."""
        try:
            # Change to git repository directory
            original_cwd = Path.cwd()
            os.chdir(self.git_repo_path)
            
            # Check for conflicts
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if "UU" not in result.stdout and "AA" not in result.stdout:
                print("✅ No conflicts detected")
                return True
            
            print("⚠️  Conflicts detected. Please resolve manually:")
            print("1. Edit conflicted files")
            print("2. Run 'git add <file>' for resolved files")
            print("3. Run 'git commit' to complete merge")
            print("4. Run this tool again to continue sync")
            
            return False
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            return False
        finally:
            # Restore original working directory
            os.chdir(original_cwd)


def main():
    """Main CLI for location sync tool."""
    parser = argparse.ArgumentParser(description="Location Sync Tool")
    parser.add_argument("--db", default="./location_classifier.db", help="SQLite database path")
    parser.add_argument("--repo", required=True, help="Git repository path")
    parser.add_argument("--labels-dir", default="location_labels", help="Labels directory in repo")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Export labels
    export_parser = subparsers.add_parser("export", help="Export location labels")
    export_parser.add_argument("--output", help="Output file path")
    
    # Import labels
    import_parser = subparsers.add_parser("import", help="Import location labels")
    import_parser.add_argument("input_file", help="Input JSON file")
    import_parser.add_argument("--merge-strategy", choices=["skip_existing", "update_existing", "create_new"], 
                             default="skip_existing", help="Merge strategy for existing locations")
    
    # Commit and push
    commit_parser = subparsers.add_parser("commit", help="Commit and push changes")
    commit_parser.add_argument("--message", help="Commit message")
    
    # Pull and import
    pull_parser = subparsers.add_parser("pull", help="Pull and import remote changes")
    pull_parser.add_argument("--merge-strategy", choices=["skip_existing", "update_existing", "create_new"], 
                            default="skip_existing", help="Merge strategy for existing locations")
    
    # Full sync
    sync_parser = subparsers.add_parser("sync", help="Full sync with remote")
    sync_parser.add_argument("--merge-strategy", choices=["skip_existing", "update_existing", "create_new"], 
                           default="skip_existing", help="Merge strategy for existing locations")
    
    # Status
    status_parser = subparsers.add_parser("status", help="Show status")
    
    # Resolve conflicts
    resolve_parser = subparsers.add_parser("resolve", help="Help resolve conflicts")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize sync tool
    db_path = Path(args.db)
    repo_path = Path(args.repo)
    sync_tool = LocationSync(db_path, repo_path, args.labels_dir)
    
    # Execute command
    if args.command == "export":
        output_file = Path(args.output) if args.output else None
        sync_tool.export_labels(output_file)
    
    elif args.command == "import":
        input_file = Path(args.input_file)
        imported, skipped = sync_tool.import_labels(input_file, args.merge_strategy)
        print(f"📊 Import Results:")
        print(f"  Imported: {imported}")
        print(f"  Skipped: {skipped}")
    
    elif args.command == "commit":
        sync_tool.commit_and_push(args.message)
    
    elif args.command == "pull":
        imported, skipped = sync_tool.pull_and_import(args.merge_strategy)
        print(f"📊 Pull Results:")
        print(f"  Imported: {imported}")
        print(f"  Skipped: {skipped}")
    
    elif args.command == "sync":
        sync_tool.sync_with_remote(args.merge_strategy)
    
    elif args.command == "status":
        sync_tool.show_status()
    
    elif args.command == "resolve":
        sync_tool.resolve_conflicts()


if __name__ == "__main__":
    import os
    main()
