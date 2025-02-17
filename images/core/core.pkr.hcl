build {
  sources = [
    "qemu.ubuntu-24"
  ]

  provisioner "shell" {
    inline = [
      "git clone https://github.com/infraguys/genesis_core.git",
    ]
  }
}
