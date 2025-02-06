from typing import Dict, List, Optional
import socket
import struct
import threading
import time
import os
import numpy as np
from dataclasses import dataclass
from enum import Enum
import asyncio
import ctypes
from concurrent.futures import ThreadPoolExecutor

class NetworkProtocol(Enum):
    UDP_MULTICAST = 1
    TCP_DIRECT = 2
    RDMA = 3
    IPC = 4

@dataclass
class NetworkStats:
    latency_ns: int
    jitter_ns: int
    packet_loss: float
    throughput_mbps: float
    connection_count: int

class NetworkOptimizer:
    """Network optimization for co-location and low latency"""
    
    def __init__(
        self,
        config: Dict,
        logger,
        error_handler
    ):
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Network settings
        self.interface = config.get('network_interface', 'eth0')
        self.ip_address = config.get('ip_address', '10.0.0.1')
        self.multicast_group = config.get('multicast_group', '239.0.0.1')
        self.port = config.get('port', 5555)
        
        # Performance monitoring
        self._latency_samples = []
        self._packet_stats = {}
        self._connection_stats = {}
        
        # Thread pool for network operations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=config.get('network_threads', 4)
        )
        
        # Initialize network optimizations
        self._init_network()
        
        # Start monitoring
        self._start_monitor()
    
    def _init_network(self) -> None:
        """Initialize network optimizations"""
        try:
            # Set up network buffers
            self._configure_socket_buffers()
            
            # Configure NIC settings
            self._configure_nic()
            
            # Set up multicast
            self._setup_multicast()
            
            # Configure interrupt handling
            self._configure_interrupts()
            
            # Initialize RDMA if available
            if self._check_rdma_support():
                self._setup_rdma()
            
            self.logger.log_event(
                "NETWORK_INIT",
                "Network optimizations initialized"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Network initialization failed: {str(e)}")
            )
    
    def _configure_socket_buffers(self) -> None:
        """Configure socket buffers for optimal performance"""
        try:
            # Set kernel parameters
            with open('/proc/sys/net/core/rmem_max', 'w') as f:
                f.write('268435456')  # 256MB
            with open('/proc/sys/net/core/wmem_max', 'w') as f:
                f.write('268435456')  # 256MB
            
            # Set UDP buffer sizes
            with open('/proc/sys/net/ipv4/udp_mem', 'w') as f:
                f.write('8388608 12582912 16777216')  # 8MB 12MB 16MB
                
            # Disable TCP slow start
            with open('/proc/sys/net/ipv4/tcp_slow_start_after_idle', 'w') as f:
                f.write('0')
            
            # Optimize TCP for low latency
            with open('/proc/sys/net/ipv4/tcp_low_latency', 'w') as f:
                f.write('1')
                
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Socket buffer configuration failed: {str(e)}")
            )
    
    def _configure_nic(self) -> None:
        """Configure Network Interface Card settings"""
        try:
            # Disable interrupt coalescence
            os.system(f'ethtool -C {self.interface} rx-usecs 0 rx-frames 1')
            
            # Enable receive side scaling
            os.system(f'ethtool -K {self.interface} rxhash on')
            
            # Set adaptive interrupt moderation
            os.system(f'ethtool -C {self.interface} adaptive-rx on')
            
            # Set ring buffer sizes
            os.system(f'ethtool -G {self.interface} rx 4096 tx 4096')
            
            # Enable pause frame flow control
            os.system(f'ethtool -A {self.interface} rx on tx on')
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"NIC configuration failed: {str(e)}")
            )
    
    def _setup_multicast(self) -> None:
        """Set up multicast networking"""
        try:
            # Create multicast socket
            self.multicast_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP
            )
            
            # Set socket options
            self.multicast_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR, 1
            )
            
            # Bind to interface
            self.multicast_socket.bind((self.ip_address, self.port))
            
            # Join multicast group
            mreq = struct.pack(
                "4s4s",
                socket.inet_aton(self.multicast_group),
                socket.inet_aton(self.ip_address)
            )
            self.multicast_socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                mreq
            )
            
            # Set TTL
            self.multicast_socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_TTL,
                2
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Multicast setup failed: {str(e)}")
            )
    
    def _configure_interrupts(self) -> None:
        """Configure network interrupt handling"""
        try:
            # Get network interface interrupts
            with open('/proc/interrupts', 'r') as f:
                interrupts = f.readlines()
            
            network_interrupts = []
            for i, line in enumerate(interrupts):
                if self.interface in line:
                    irq = line.split(':')[0].strip()
                    network_interrupts.append(irq)
            
            # Set interrupt affinity
            cpu_cores = self.config.get('network_cores', [0, 1])
            for i, irq in enumerate(network_interrupts):
                core = cpu_cores[i % len(cpu_cores)]
                mask = 1 << core
                
                with open(f'/proc/irq/{irq}/smp_affinity', 'w') as f:
                    f.write(f'{mask:x}')
            
            # Set IRQ balance settings
            os.system('systemctl stop irqbalance')
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Interrupt configuration failed: {str(e)}")
            )
    
    def _check_rdma_support(self) -> bool:
        """Check for RDMA support"""
        try:
            return os.path.exists('/dev/infiniband/uverbs0')
        except Exception:
            return False
    
    def _setup_rdma(self) -> None:
        """Set up RDMA if available"""
        try:
            # Import RDMA libraries
            import pyverbs.device as d
            import pyverbs.pd as pd
            import pyverbs.qp as qp
            import pyverbs.cq as cq
            
            # Get RDMA device
            devices = d.get_device_list()
            if not devices:
                raise NetworkError("No RDMA devices found")
            
            self.rdma_device = devices[0]
            self.rdma_context = self.rdma_device.open()
            
            # Create protection domain
            self.pd = pd.PD(self.rdma_context)
            
            # Create completion queues
            self.send_cq = cq.CQ(self.rdma_context, 100)
            self.recv_cq = cq.CQ(self.rdma_context, 100)
            
            # Create queue pair
            self.qp = qp.QP(self.pd, qp.IBV_QPT_RC)
            
            self.logger.log_event(
                "RDMA_INIT",
                "RDMA initialized successfully"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"RDMA setup failed: {str(e)}")
            )
    
    def send_market_data(
        self,
        data: bytes,
        protocol: NetworkProtocol = NetworkProtocol.UDP_MULTICAST
    ) -> bool:
        """Send market data using specified protocol"""
        try:
            if protocol == NetworkProtocol.UDP_MULTICAST:
                return self._send_multicast(data)
            elif protocol == NetworkProtocol.RDMA:
                return self._send_rdma(data)
            elif protocol == NetworkProtocol.IPC:
                return self._send_ipc(data)
            else:
                return self._send_tcp(data)
                
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Market data send failed: {str(e)}")
            )
            return False
    
    def _send_multicast(self, data: bytes) -> bool:
        """Send data via multicast"""
        try:
            bytes_sent = self.multicast_socket.sendto(
                data,
                (self.multicast_group, self.port)
            )
            
            return bytes_sent == len(data)
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Multicast send failed: {str(e)}")
            )
            return False
    
    def _send_rdma(self, data: bytes) -> bool:
        """Send data via RDMA"""
        try:
            if not hasattr(self, 'qp'):
                return False
                
            # Register memory buffer
            mr = self.pd.reg_mr(data)
            
            # Post send request
            self.qp.post_send(mr)
            
            # Wait for completion
            wc = self.send_cq.poll()
            
            return wc[0].status == 0
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"RDMA send failed: {str(e)}")
            )
            return False
    
    def _send_ipc(self, data: bytes) -> bool:
        """Send data via IPC shared memory"""
        try:
            # Write to shared memory
            self.mmap_file.seek(0)
            self.mmap_file.write(data)
            
            # Signal receiving process
            os.kill(self.receiver_pid, signal.SIGUSR1)
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"IPC send failed: {str(e)}")
            )
            return False
    
    def _start_monitor(self) -> None:
        """Start network monitoring"""
        def monitor():
            while True:
                try:
                    self._update_network_stats()
                    time.sleep(1)
                except Exception as e:
                    self.error_handler.handle_error(
                        NetworkError(f"Network monitoring failed: {str(e)}")
                    )
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _update_network_stats(self) -> None:
        """Update network performance statistics"""
        try:
            # Measure latency
            latency = self._measure_latency()
            self._latency_samples.append(latency)
            
            # Keep only recent samples
            if len(self._latency_samples) > 1000:
                self._latency_samples = self._latency_samples[-1000:]
            
            # Update packet statistics
            self._update_packet_stats()
            
            # Monitor connection status
            self._update_connection_stats()
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Stats update failed: {str(e)}")
            )
    
    def _measure_latency(self) -> int:
        """Measure network latency in nanoseconds"""
        try:
            start_time = time.time_ns()
            
            # Send ping packet
            self.multicast_socket.sendto(
                b'ping',
                (self.multicast_group, self.port)
            )
            
            # Receive response
            self.multicast_socket.recv(4)
            
            end_time = time.time_ns()
            
            return (end_time - start_time) // 2  # Round-trip time / 2
            
        except Exception:
            return 0
    
    def get_network_stats(self) -> NetworkStats:
        """Get current network statistics"""
        try:
            if not self._latency_samples:
                return NetworkStats(0, 0, 0.0, 0.0, 0)
            
            return NetworkStats(
                latency_ns=int(np.mean(self._latency_samples)),
                jitter_ns=int(np.std(self._latency_samples)),
                packet_loss=self._calculate_packet_loss(),
                throughput_mbps=self._calculate_throughput(),
                connection_count=len(self._connection_stats)
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                NetworkError(f"Stats calculation failed: {str(e)}")
            )
            return NetworkStats(0, 0, 0.0, 0.0, 0)

class NetworkError(Exception):
    """Custom exception for network-related errors"""
    pass
