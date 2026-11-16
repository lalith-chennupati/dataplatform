# A01 - PowerScale OneFS fundamentals

| Tier | Time | Domains | Prerequisites |
|---|---|---|---|
| SIM (OneFS Simulator) / HW | 3 h | STO | L01 Step 6 (`$PS` reachable) |

## Prerequisites
- `ssh root@$PS isi status` works.
- A Linux client (the Docker host is fine) with `nfs-common` and `cifs-utils` installed. Python `boto3` comes from L01 Step 7.
- A DNS server you can add a delegation to, or `/etc/hosts` edits for SmartConnect testing.

## Steps

### Step 1 - Explore the cluster
```bash
ssh root@$PS
isi status                      # node health, capacity, throughput
isi storagepool nodepools list  # node pools (tiers)
isi network interfaces list     # which NICs are in which pool
isi network pools list -v       # IP pools and SmartConnect settings
ls /ifs                         # the single namespace
```
Note: node count, usable capacity, OneFS version and the default pool name (usually `groupnet0.subnet0.pool0`).

### Step 2 - Configure SmartConnect
```bash
isi network subnets modify groupnet0.subnet0 --sc-service-addrs=10.10.10.50
isi network pools modify groupnet0.subnet0.pool0 \
  --sc-dns-zone=ai.ps-lab.local --sc-connect-policy=round_robin --alloc-method=dynamic
```
On your DNS server, delegate `ai.ps-lab.local` to the SmartConnect service IP: an NS record pointing to an A record for `10.10.10.50`. Then test:
```bash
for i in 1 2 3 4; do nslookup ai.ps-lab.local | awk '/Address/ && !/#/ {print $2}'; done
```
Expected: the answers rotate across the node IPs. (Without a DNS delegation, skip this step and use node IPs. Record that SmartConnect was not tested.)

### Step 3 - Create an AI dataset directory
```bash
mkdir -p /ifs/data/ai/datasets /ifs/data/ai/checkpoints
chmod 775 /ifs/data/ai
```

### Step 4 - Export over NFS
```bash
isi nfs exports create /ifs/data/ai --zone=System \
  --clients=10.10.10.0/24 --root-clients=10.10.10.0/24 --description="AI datasets"
isi nfs exports list
```
On the Linux client:
```bash
sudo mkdir -p /mnt/ps-ai
sudo mount -t nfs -o vers=4.1 ai.ps-lab.local:/ifs/data/ai /mnt/ps-ai     # or $PS:/ifs/data/ai
echo "written over NFS" | sudo tee /mnt/ps-ai/datasets/hello.txt
```

### Step 5 - Share over SMB
```bash
isi smb shares create ai /ifs/data/ai --zone=System --description="AI datasets"
isi smb shares permission modify ai --zone=System --wellknown Everyone -d full --permission-type allow   # lab only
```
From the client: `sudo mount -t cifs //$PS/ai /mnt/ps-ai-smb -o username=root` and read `datasets/hello.txt`.

### Step 6 - Enable S3 and create a bucket on the same path
```bash
isi services s3 enable
isi s3 settings global view
isi s3 buckets create --name=ai-datasets --path=/ifs/data/ai/datasets --owner=root --zone=System
isi s3 keys create root --zone=System          # prints access ID and secret key, save them
```
From the client:
```bash
export AWS_ACCESS_KEY_ID=<access id> AWS_SECRET_ACCESS_KEY=<secret>
aws --endpoint-url https://$PS:9021 --no-verify-ssl s3 ls s3://ai-datasets/
aws --endpoint-url https://$PS:9021 --no-verify-ssl s3 cp s3://ai-datasets/hello.txt -
```
Expected: `written over NFS`. One file, two protocols, no copy.

### Step 7 - (Optional) HDFS
```bash
isi services hdfs enable
isi hdfs settings modify --zone=System --root-directory=/ifs/data/ai
```
Any Hadoop client pointed at `hdfs://ai.ps-lab.local:8020/` now sees the same files.

### Step 8 - Compare permissions across protocols
1. `ls -l /mnt/ps-ai/datasets/hello.txt` (POSIX mode bits).
2. `ssh root@$PS ls -le /ifs/data/ai/datasets/hello.txt` (OneFS ACL view).
3. Write a second file over SMB as a Windows/AD user and look at its owner from NFS.
4. `isi zone zones view System | grep -i "permission"`. Note the ACL policy, e.g. *balanced*. That setting decides how mode bits and ACLs interact.

## Verify
- [ ] One file is readable over NFS, SMB and S3 (and HDFS if enabled).
- [ ] SmartConnect spreads connections across nodes, or a note says it was not tested.
- [ ] The permission behaviour per protocol is documented in the evidence log.

## Record for the standards
- `STO-01`: PowerScale role (file / multiprotocol). `STO-02`: which protocols you will support.
- `ARC-03`: naming pattern for SmartConnect zones and export paths (e.g. `/ifs/<zone>/<tenant>/<dataset>`).

## Cleanup
```bash
sudo umount /mnt/ps-ai /mnt/ps-ai-smb
ssh root@$PS
isi s3 buckets delete ai-datasets --zone=System --force
isi smb shares delete ai --zone=System --force
isi nfs exports list --zone=System            # note the ID of the /ifs/data/ai export
isi nfs exports delete <id> --zone=System --force
```
