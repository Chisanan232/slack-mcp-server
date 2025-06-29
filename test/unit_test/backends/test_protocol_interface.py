"""
Unit tests for the QueueBackend protocol interface.

These tests verify the structural aspects of the protocol definition itself,
ensuring that the required methods and signatures are correctly defined.
Protocol methods with ellipsis (...) placeholders are excluded from coverage
reporting via .coveragerc configuration.
"""

from slack_mcp.backends.protocol import QueueBackend


class TestQueueBackendInterface:
    """Tests focused on the QueueBackend protocol interface structure."""

    def test_protocol_definition(self):
        """Verify the protocol interface is correctly defined with required methods.
        
        This test checks that:
        1. The protocol methods contain ellipsis placeholders as expected
        2. All required methods (publish, consume) exist
        3. The classmethod from_env is properly defined
        
        Protocol methods with ellipsis (...) are properly excluded from coverage
        requirements via the .coveragerc configuration, as they are interface
        definitions rather than executable code.
        """
        from inspect import getsource
        
        # Get the source code of the protocol methods
        publish_source = getsource(QueueBackend.publish)
        consume_source = getsource(QueueBackend.consume)
        
        # Verify method bodies contain ellipsis as expected for Protocol interface definitions
        assert "..." in publish_source, "publish method should have ellipsis placeholder"
        assert "..." in consume_source, "consume method should have ellipsis placeholder"
        
        # Verify from_env exists as a classmethod on the protocol
        assert hasattr(QueueBackend, "from_env"), "from_env classmethod should exist on the protocol"
        
        # Verify the expected method names exist on the protocol
        expected_methods = {"publish", "consume"}
        protocol_methods = {name for name in dir(QueueBackend) 
                          if not name.startswith("_") and name not in {"from_env"}}
        assert expected_methods == protocol_methods, (
            f"QueueBackend protocol should define these methods: {expected_methods}, "
            f"but it defines: {protocol_methods}"
        )
