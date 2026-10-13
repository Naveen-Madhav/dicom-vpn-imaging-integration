# DICOM validation matrix

| Check | Command or evidence | Pass condition |
| --- | --- | --- |
| IKE peer state | swanctl --list-sas | established IKE and child SAs |
| Network reachability | network_preflight_check.py | target responds and required ports connect |
| Calling AE authorization | DICOM C-ECHO with a registered title | association accepted |
| Unknown AE rejection | C-ECHO with an unregistered title | association rejected or operation returns failure |
| Single store | verification client with one DICOM file | status 0x0000 |
| Series store | verification client with a directory | every instance returns 0x0000 |
| PACS persistence | Orthanc API or storage index | instance is queryable |
| Route fan-out | PACS and VNA/radiology logs | configured destinations receive the instance |
| MTU boundary | DF ping near the tunnel payload limit | no fragmentation loss |

The master_test_runner.py command records execution status and duration. It accepts target host, port, AE titles, and an option to omit the network preflight when the network is managed separately.

