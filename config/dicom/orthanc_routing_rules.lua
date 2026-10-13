function Initialize()
    PrintToLog("INFO: PACS routing policy loaded")
end

function OnStoredInstance(instanceId, tags, metadata, origin)
    local description = string.upper(tags['StudyDescription'] or '')
    local modality = tags['Modality'] or 'unknown'
    local callingAet = origin['CallingAet'] or 'unknown'

    PrintToLog(string.format(
        "C-STORE received from %s modality=%s",
        callingAet, modality
    ))

    if string.find(description, "STAT") or
       string.find(description, "TRAUMA") or
       string.find(description, "STROKE") or
       string.find(description, "EMERGENCY") then
        SendToModality(instanceId, 'RAD_DESK_01')
    end

    SendToModality(instanceId, 'CORP_VNA')
end

function ReceivedSliceFilter(tags)
    return tags['PatientID'] ~= nil and tags['SOPClassUID'] ~= nil
end
