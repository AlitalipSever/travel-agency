output "server_ipv4" {
  description = "Public IPv4 of the server: the Cloudflare A record and the SSH target."
  value       = hcloud_server.k3s.ipv4_address
}

output "server_ipv6" {
  description = "Public IPv6 of the server (optional AAAA record)."
  value       = hcloud_server.k3s.ipv6_address
}

output "kubeconfig_hint" {
  description = "How to fetch the cluster credentials to the laptop once cloud-init has finished."
  value       = <<-EOT
    scp -i ~/.ssh/travel-agency-hetzner root@${hcloud_server.k3s.ipv4_address}:/etc/rancher/k3s/k3s.yaml ~/.kube/travel-agency.yaml
    sed -i '' 's/127.0.0.1/${hcloud_server.k3s.ipv4_address}/' ~/.kube/travel-agency.yaml
    chmod 600 ~/.kube/travel-agency.yaml
    export KUBECONFIG=~/.kube/travel-agency.yaml
  EOT
}
