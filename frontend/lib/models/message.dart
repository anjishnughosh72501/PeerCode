class BridgeMessage {
  const BridgeMessage({required this.type, required this.payload});

  final String type;
  final Map<String, Object?> payload;
}
