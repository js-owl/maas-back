"""Check all stages in MaaS funnel"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.bitrix.client import bitrix_client
from backend.bitrix.funnel_manager import funnel_manager

async def check():
    """Check all stages in MaaS funnel"""
    print("=" * 100)
    print("MaaS FUNNEL STAGES CHECK")
    print("=" * 100)
    
    # Ensure funnel is initialized
    if not funnel_manager.is_initialized():
        await funnel_manager.ensure_maas_funnel()
    
    category_id = funnel_manager.get_category_id()
    print(f"\nCategory ID: {category_id}")
    
    # Get all stages for this category
    stages = await bitrix_client.get_category_stages(category_id)
    
    if stages:
        print(f"\nFound {len(stages)} stages in MaaS funnel:\n")
        print(f"{'Stage ID':<25} {'Stage Name':<40} {'Semantics':<15} {'Sort':<10}")
        print("-" * 100)
        
        for stage in stages:
            stage_id = stage.get("STATUS_ID") or stage.get("status_id", "N/A")
            stage_name = stage.get("NAME") or stage.get("name", "N/A")
            semantics = stage.get("SEMANTICS") or stage.get("semantics", "N/A")
            sort = stage.get("SORT") or stage.get("sort", "N/A")
            print(f"{stage_id:<25} {stage_name:<40} {semantics:<15} {sort:<10}")
        
        print("\n" + "=" * 100)
        print("CURRENT MAPPINGS")
        print("=" * 100)
        status_mapping = funnel_manager.get_status_mapping()
        print(f"\nMapped stages ({len(status_mapping)}):")
        for stage_id, status in status_mapping.items():
            stage_info = next((s for s in stages if (s.get("STATUS_ID") or s.get("status_id")) == stage_id), None)
            stage_name = stage_info.get("NAME") or stage_info.get("name", "N/A") if stage_info else "N/A"
            print(f"  {stage_id:<25} ({stage_name:<40}) → {status}")
        
        print(f"\nUnmapped stages:")
        unmapped = []
        for stage in stages:
            stage_id = stage.get("STATUS_ID") or stage.get("status_id")
            if stage_id and stage_id not in status_mapping:
                stage_name = stage.get("NAME") or stage.get("name", "N/A")
                unmapped.append((stage_id, stage_name))
                print(f"  {stage_id:<25} {stage_name}")
        
        if not unmapped:
            print("  (none - all stages are mapped)")
    else:
        print("\nNo stages found or error retrieving stages")

if __name__ == "__main__":
    asyncio.run(check())


