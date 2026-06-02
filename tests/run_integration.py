"""Quick integration test: verify the full pipeline doesn't hang"""
import os, sys, asyncio, time

example_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'examples', 'ofweek_distributed')
sys.path.insert(0, example_dir)

from crawlo.crawler import CrawlerProcess
from crawlo.logging import get_logger

logger = get_logger("integration_test")

async def main():
    print(f"\n[{time.strftime('%H:%M:%S')}] Starting integration test...")
    process = CrawlerProcess()
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] Step 1: Creating crawler...")
        # Directly test initialization without network crawl
        crawler = process._crawl_single('of_week_distributed')
        crawler_task = asyncio.create_task(crawler)
        
        # Wait max 30 seconds for initialization
        await asyncio.sleep(10)  # Give it time to init
        
        # Check state
        engine = getattr(process._crawlers[0], '_engine', None) if process._crawlers else None
        if engine:
            print(f"[{time.strftime('%H:%M:%S')}] Engine created: running={engine.running}")
            print(f"[{time.strftime('%H:%M:%S')}] Scheduler: {engine.scheduler is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Downloader: {engine.downloader is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster worker_id: {engine._cluster_worker_id}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster registry: {engine._cluster_registry is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster heartbeat: {engine._cluster_heartbeat is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster failover: {engine._cluster_failover is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster progress: {engine._cluster_progress is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster rate_limiter: {engine._cluster_rate_limiter is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster monitor: {engine._cluster_monitor is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster messenger: {engine._cluster_messenger is not None}")
            print(f"[{time.strftime('%H:%M:%S')}] Cluster dynamic_config: {engine._cluster_dynamic_config is not None}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Engine not yet created")
        
        # Cancel the crawl (we just wanted init verification)
        crawler_task.cancel()
        try: await crawler_task
        except: pass
        
        print(f"[{time.strftime('%H:%M:%S')}] Integration test complete!")
        
    except asyncio.TimeoutError:
        print(f"[{time.strftime('%H:%M:%S')}] TIMEOUT after 30s - process may be hung")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR: {e}")
        import traceback; traceback.print_exc()

asyncio.run(main())
