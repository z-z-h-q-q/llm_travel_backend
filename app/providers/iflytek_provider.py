"""
Stub module for iFlyTek provider.

The original implementation has been removed for safety. This file remains
as a stub to prevent import errors in environments where references were not
fully removed. Any attempt to call the original functions will raise a
RuntimeError with guidance to use client-side recognition or reconfigure a
different provider.
"""

def _removed(*args, **kwargs):
    raise RuntimeError(
        "iFlyTek provider was removed from this deployment. "
        "Use client-side Web Speech API or configure a server-side speech provider."
    )


async def extract_basicinfo_with_iflytek(text: str) -> dict:
    _removed()


def make_iflytek_ws_url(*args, **kwargs):
    _removed()


async def recognize_iat_ws_v2(*args, **kwargs):
    _removed()
