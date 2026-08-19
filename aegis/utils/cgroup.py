import os
import glob
from typing import List

MIN_LIMIT_BYTES = 512 * 1024 * 1024  # 512 MiB safety floor

class CGroupManager:
    def __init__(self):
        self.cgroup_base = "/sys/fs/cgroup"
        self.target_dirs: List[str] = []
        self._discover_cgroups()

    def _discover_cgroups(self):
        """Find writable app.slice or session.slice directories."""
        found = []
        for pat in [
            "/sys/fs/cgroup/user.slice/user-*.slice/user@*.service/app.slice",
            "/sys/fs/cgroup/user.slice/user-*.slice/session-*.scope",
            "/sys/fs/cgroup/app.slice",
            "/sys/fs/cgroup/session.slice",
        ]:
            for path in glob.glob(pat):
                if os.path.isdir(path) and os.access(path, os.W_OK):
                    found.append(path)

        if not found and os.access(self.cgroup_base, os.W_OK):
            found.append(self.cgroup_base)

        self.target_dirs = list(set(found))

    def limit_dirs(self) -> List[str]:
        return self.target_dirs

    def apply_limits(self, soft_bytes: int, max_bytes: int) -> bool:
        """Write memory.high and memory.max limits to discovered cgroups."""
        if not self.target_dirs:
            return False

        soft_bytes = max(soft_bytes, MIN_LIMIT_BYTES)
        max_bytes = max(max_bytes, MIN_LIMIT_BYTES)

        success = False
        for cdir in self.target_dirs:
            high_file = os.path.join(cdir, "memory.high")
            max_file = os.path.join(cdir, "memory.max")

            try:
                if os.path.exists(high_file):
                    with open(high_file, "w") as f:
                        f.write(str(soft_bytes))
                if os.path.exists(max_file):
                    with open(max_file, "w") as f:
                        f.write(str(max_bytes))
                success = True
            except Exception:
                continue

        return success

    def restore_limits(self):
        """Reset limits to 'max' on clean stop."""
        for cdir in self.target_dirs:
            high_file = os.path.join(cdir, "memory.high")
            max_file = os.path.join(cdir, "memory.max")
            try:
                if os.path.exists(high_file):
                    with open(high_file, "w") as f:
                        f.write("max")
                if os.path.exists(max_file):
                    with open(max_file, "w") as f:
                        f.write("max")
            except Exception:
                pass
