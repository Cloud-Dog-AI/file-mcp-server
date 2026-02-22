from setuptools import find_packages, setup


setup(
    name="file-mcp-server",
    version="0.1.0",
    description="File MCP server and reusable file tools",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["file_mcp_server*", "file_tools*"]),
    install_requires=[],
    extras_require={
        "dev": [],
        "test": [],
    },
)
