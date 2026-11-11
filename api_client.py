import aiohttp
from typing import Dict, Any, Optional
import config

class APIClient:
    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.api_key = config.API_KEY

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }

    async def create_key(self, username: Optional[str], days: int) -> Dict[str, Any]:
        """
        Creates a license key for the given duration in days.
        If username is provided, binds to that username.
        """
        url = f"{self.base_url}/keys/create"
        payload = {"days": days}
        if username:
            payload["username"] = username.strip()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self._headers(), json=payload, timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def reset_hwid(self, key_or_username: str) -> Dict[str, Any]:
        """
        Resets the hardware ID (HWID) binding for a license key or username.
        """
        url = f"{self.base_url}/keys/reset-hwid"
        payload = {"username": key_or_username.strip()}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self._headers(), json=payload, timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def delete_key(self, key_or_username: str) -> Dict[str, Any]:
        """
        Permanently revokes/deletes a license key.
        """
        url = f"{self.base_url}/keys/delete"
        payload = {"username": key_or_username.strip()}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self._headers(), json=payload, timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def get_key_info(self, key_or_username: str) -> Dict[str, Any]:
        """
        Fetches license key details and expiry.
        """
        url = f"{self.base_url}/keys/info/{key_or_username.strip()}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers(), timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def list_keys(self) -> Dict[str, Any]:
        """
        Lists all keys created under this API key.
        """
        url = f"{self.base_url}/keys/list"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers(), timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    async def get_profile(self) -> Dict[str, Any]:
        """
        Fetches quota, balance, and account status from upstream API.
        """
        url = f"{self.base_url}/profile"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self._headers(), timeout=15) as resp:
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {"success": False, "error": await resp.text()}
                    data["status_code"] = resp.status
                    return data
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

api = APIClient()
