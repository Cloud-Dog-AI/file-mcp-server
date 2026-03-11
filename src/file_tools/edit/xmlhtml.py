"""
file-mcp-server — file_tools/edit/xmlhtml.py

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Ltd.
Description: File tools module for edit xmlhtml.py.
"""

from __future__ import annotations

from typing import Optional

from bs4 import BeautifulSoup
from lxml import etree


def xml_get(text: str, xpath: str) -> Optional[str]:
    """Execute xml get."""
    tree = etree.fromstring(text.encode("utf-8"))
    result = tree.xpath(xpath)
    if isinstance(result, list):
        if not result:
            return None
        node = result[0]
        if isinstance(node, etree._Element):
            return etree.tostring(node, encoding="unicode")
        return str(node)
    return str(result)


def xml_set(text: str, xpath: str, value: str) -> str:
    """Execute xml set."""
    tree = etree.fromstring(text.encode("utf-8"))
    result = tree.xpath(xpath)
    nodes = result if isinstance(result, list) else []
    if not nodes:
        raise ValueError("XPath did not match any node")
    for node in nodes:
        if isinstance(node, etree._Element):
            node.text = value
    return etree.tostring(tree, encoding="unicode")


def xml_delete(text: str, xpath: str) -> str:
    """Execute xml delete."""
    tree = etree.fromstring(text.encode("utf-8"))
    result = tree.xpath(xpath)
    nodes = result if isinstance(result, list) else []
    for node in nodes:
        if isinstance(node, etree._Element):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
    return etree.tostring(tree, encoding="unicode")


def html_get(text: str, selector: str) -> Optional[str]:
    """Execute html get."""
    soup = BeautifulSoup(text, "html.parser")
    node = soup.select_one(selector)
    return str(node) if node else None


def html_set(text: str, selector: str, value: str) -> str:
    """Execute html set."""
    soup = BeautifulSoup(text, "html.parser")
    nodes = soup.select(selector)
    if not nodes:
        raise ValueError("Selector did not match any node")
    for node in nodes:
        node.string = value
    return str(soup)


def html_delete(text: str, selector: str) -> str:
    """Execute html delete."""
    soup = BeautifulSoup(text, "html.parser")
    nodes = soup.select(selector)
    for node in nodes:
        node.decompose()
    return str(soup)
