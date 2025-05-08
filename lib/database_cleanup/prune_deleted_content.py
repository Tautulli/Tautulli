"""
Tautulli Orphaned History Pruner
Standalone script to remove watch history entries for media no longer in Plex
"""

import argparse
import asyncio
import logging
import sqlite3
from contextlib import contextmanager
from plexapi.server import PlexServer
from typing import Set, List

# Configure logging
logger = logging.getLogger("tautulli-pruner")
log_handler = logging.StreamHandler()
log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)


@contextmanager
def database_connection(db_path: str):
    """Context manager for SQLite database connections."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class PlexManager:
    """Handles Plex server communication with async support"""

    def __init__(self, base_url: str, token: str, server_name: str = None):
        self.plex = PlexServer(base_url, token)
        self.server_name = server_name or self.plex.friendlyName

    async def fetch_all_media_ids(self) -> Set[int]:
        """Fetch all rating keys from relevant Plex libraries"""
        media_ids = set()
        loop = asyncio.get_event_loop()

        try:
            sections = await loop.run_in_executor(None, self.plex.library.sections)
            for section in sections:
                if section.type in ("movie", "show"):
                    try:
                        items = await loop.run_in_executor(None, section.all)
                        media_ids.update(item.ratingKey for item in items)
                        logger.debug(f"Processed {section.title} ({len(items)} items)")
                    except Exception as e:
                        logger.error(f"Error processing {section.title}: {e}")
        except Exception as e:
            logger.error(f"Plex connection failed: {e}")

        return media_ids


class HistoryPruner:
    """Handles orphaned history detection and removal"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_watch_history(self) -> List[int]:
        """Retrieve all rating keys from watch history"""
        with database_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rating_key FROM watch_history")
            return [row["rating_key"] for row in cursor.fetchall()]

    def delete_orphans(self, rating_keys: List[int]):
        """Batch delete orphaned entries efficiently"""
        if not rating_keys:
            logger.info("No orphans to delete")
            return

        chunk_size = 999  # SQLite parameter limit
        total_deleted = 0

        with database_connection(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")
                for i in range(0, len(rating_keys), chunk_size):
                    chunk = rating_keys[i : i + chunk_size]
                    placeholders = ",".join(["?"] * len(chunk))
                    cursor.execute(
                        f"DELETE FROM watch_history WHERE rating_key IN ({placeholders})",
                        chunk,
                    )
                    total_deleted += cursor.rowcount
                cursor.execute("COMMIT")
                logger.info(f"Deleted {total_deleted} orphaned entries")
            except sqlite3.Error as e:
                cursor.execute("ROLLBACK")
                logger.error(f"Database error: {e}")
                raise


async def main(args):
    """Orphan pruning workflow"""
    logger.setLevel(args.loglevel)

    # Initialize components
    plex = PlexManager(args.plex_url, args.plex_token, args.plex_server)
    pruner = HistoryPruner(args.db_path)

    try:
        # Fetch data from sources
        logger.info("Fetching Plex media IDs...")
        plex_ids = await plex.fetch_all_media_ids()
        logger.info(f"Found {len(plex_ids)} Plex media items")

        logger.info("Fetching Tautulli watch history...")
        history_ids = pruner.get_watch_history()
        logger.info(f"Found {len(history_ids)} watch history entries")

        # Calculate orphans
        orphans = list(set(history_ids) - plex_ids)
        logger.info(f"Identified {len(orphans)} orphaned entries")

        pruner.delete_orphans(orphans)

    except Exception as e:
        logger.error(f"Pruning failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tautulli orphaned history pruner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--db-path", required=True, help="Path to Tautulli database file (tautulli.db)"
    )
    parser.add_argument(
        "--plex-url", required=True, help="Plex server URL (e.g. http://plex:32400)"
    )
    parser.add_argument("--plex-token", required=True, help="Plex authentication token")

    # Optional arguments
    parser.add_argument("--plex-server", help="Plex server name (if multiple servers)")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase logging verbosity"
    )

    args = parser.parse_args()

    # Set log level based on verbosity
    args.loglevel = logging.WARNING
    if args.verbose == 1:
        args.loglevel = logging.INFO
    elif args.verbose >= 2:
        args.loglevel = logging.DEBUG

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        exit(1)
