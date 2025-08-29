#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL Shortener module for FileStore Bot
"""

import aiohttp
import asyncio
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class URLShortener:
    def __init__(self):
        self.enabled = Config.SHORTENER_ENABLED
        self.site = Config.SHORTENER_SITE
        self.api_key = Config.SHORTENER_API_KEY
        self.supported_sites = Config.SUPPORTED_SHORTENERS
    
    async def shorten_url(self, long_url: str) -> str:
        """Shorten a URL using the configured shortener service"""
        if not self.enabled:
            return long_url
        
        if self.site not in self.supported_sites:
            logger.error(f"Unsupported shortener site: {self.site}")
            return long_url
        
        site_config = self.supported_sites[self.site]
        
        # Check if API key is required
        if site_config["requires_key"] and not self.api_key:
            logger.error(f"API key required for {self.site} but not provided")
            return long_url
        
        try:
            if self.site == "tinyurl.com":
                return await self._shorten_tinyurl(long_url)
            elif self.site == "is.gd":
                return await self._shorten_isgd(long_url)
            elif self.site == "v.gd":
                return await self._shorten_vgd(long_url)
            elif self.site == "bit.ly":
                return await self._shorten_bitly(long_url)
            elif self.site == "short.io":
                return await self._shorten_shortio(long_url)
            elif self.site == "rebrandly.com":
                return await self._shorten_rebrandly(long_url)
            elif self.site == "cutt.ly":
                return await self._shorten_cuttly(long_url)
            elif self.site == "t.ly":
                return await self._shorten_tly(long_url)
            elif self.site == "gg.gg":
                return await self._shorten_gggg(long_url)
            else:
                logger.error(f"No implementation for {self.site}")
                return long_url
        
        except Exception as e:
            logger.error(f"Error shortening URL with {self.site}: {e}")
            return long_url
    
    async def _shorten_tinyurl(self, long_url: str) -> str:
        """Shorten URL using TinyURL"""
        async with aiohttp.ClientSession() as session:
            params = {"url": long_url}
            async with session.get("https://tinyurl.com/api-create.php", params=params) as response:
                if response.status == 200:
                    short_url = await response.text()
                    if short_url.startswith("http"):
                        return short_url.strip()
        return long_url
    
    async def _shorten_isgd(self, long_url: str) -> str:
        """Shorten URL using is.gd"""
        async with aiohttp.ClientSession() as session:
            params = {"format": "simple", "url": long_url}
            async with session.get("https://is.gd/create.php", params=params) as response:
                if response.status == 200:
                    short_url = await response.text()
                    if short_url.startswith("http"):
                        return short_url.strip()
        return long_url
    
    async def _shorten_vgd(self, long_url: str) -> str:
        """Shorten URL using v.gd"""
        async with aiohttp.ClientSession() as session:
            params = {"format": "simple", "url": long_url}
            async with session.get("https://v.gd/create.php", params=params) as response:
                if response.status == 200:
                    short_url = await response.text()
                    if short_url.startswith("http"):
                        return short_url.strip()
        return long_url
    
    async def _shorten_bitly(self, long_url: str) -> str:
        """Shorten URL using Bit.ly"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {"long_url": long_url}
            async with session.post("https://api-ssl.bitly.com/v4/shorten", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("link", long_url)
        return long_url
    
    async def _shorten_shortio(self, long_url: str) -> str:
        """Shorten URL using Short.io"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            data = {"originalURL": long_url}
            async with session.post("https://api.short.io/links", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("shortURL", long_url)
        return long_url
    
    async def _shorten_rebrandly(self, long_url: str) -> str:
        """Shorten URL using Rebrandly"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }
            data = {"destination": long_url}
            async with session.post("https://api.rebrandly.com/v1/links", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("shortUrl", long_url)
        return long_url
    
    async def _shorten_cuttly(self, long_url: str) -> str:
        """Shorten URL using Cutt.ly"""
        async with aiohttp.ClientSession() as session:
            params = {
                "key": self.api_key,
                "short": long_url
            }
            async with session.get("https://cutt.ly/api/api.php", params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("url", {}).get("status") == 7:
                        return result["url"]["shortLink"]
        return long_url
    
    async def _shorten_tly(self, long_url: str) -> str:
        """Shorten URL using T.ly"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {"long_url": long_url}
            async with session.post("https://t.ly/api/v1/link/shorten", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("short_url", long_url)
        return long_url
    
    async def _shorten_gggg(self, long_url: str) -> str:
        """Shorten URL using gg.gg"""
        async with aiohttp.ClientSession() as session:
            data = {"url": long_url}
            async with session.post("http://gg.gg/create", data=data) as response:
                if response.status == 200:
                    # gg.gg returns HTML, need to parse the short URL
                    html = await response.text()
                    if "http://gg.gg/" in html:
                        # Extract the short URL from the response
                        start = html.find("http://gg.gg/")
                        if start != -1:
                            end = html.find('"', start)
                            if end != -1:
                                return html[start:end]
        return long_url
    
    def is_enabled(self) -> bool:
        """Check if shortener is enabled"""
        return self.enabled
    
    def get_current_site(self) -> str:
        """Get current shortener site"""
        return self.site
    
    def get_supported_sites(self) -> list:
        """Get list of supported shortener sites"""
        return list(self.supported_sites.keys())
    
    def site_requires_key(self, site: str) -> bool:
        """Check if a site requires API key"""
        return self.supported_sites.get(site, {}).get("requires_key", False)

# Global shortener instance
shortener = URLShortener()