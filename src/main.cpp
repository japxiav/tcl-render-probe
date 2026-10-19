// TCL Render Probe v0.1 - strictly whitelisted read-only AIDL client.
// Target: TCL C6K / MediaTek V643, Android 14. No privileged operations.
// Mode --ping: Binder ping only. Mode --read-block-num: AIDL transaction 147 only.
#include <android/binder_ibinder.h>
#include <android/binder_parcel.h>
#include <android/binder_status.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>

namespace {
constexpr const char* kService = "vendor.mediatek.hardware.render.IRender/default";
constexpr const char* kDescriptor = "vendor.mediatek.hardware.render.IRender";
constexpr transaction_code_t kGetLdmBlockNum = 147;
constexpr transaction_code_t kGetDeviceId = 31;
// Exact selector compared by both MI_RENDER_GetLdmBlockNum and
// MI_RENDER_GetLdmBlockData in libmi3_hwc_hal.so (V643):
//   mvn r0, #0x0e000000 -> 0xf1ffffff (signed -234881025)
// Its semantic name remains unidentified. It is NOT GetDeviceId's response.
constexpr int32_t kNativeLdmSelector = -234881025;

void* onCreate(void*) { return nullptr; }
void onDestroy(void*) {}
binder_status_t onTransact(AIBinder*, transaction_code_t, const AParcel*, AParcel*) {
    return STATUS_UNKNOWN_TRANSACTION;
}

bool okay(binder_status_t result, const char* operation) {
    if (result == STATUS_OK) return true;
    std::fprintf(stderr, "ERROR: %s: Binder status %d\n", operation, result);
    return false;
}

// Wire format verified in ST_LDM_BLOCK_NUM_INFO::writeToParcel in
// vendor.mediatek.hardware.render-V1-ndk.so, ELF 0x4d841:
// [parcelable_size:i32, block_type:i32, width:char16, height:char16].
bool writeBlockNumRequest(AParcel* parcel) {
    const int32_t begin = AParcel_getDataPosition(parcel);
    if (begin < 0) return false;
    if (!okay(AParcel_writeInt32(parcel, 0), "size placeholder")) return false;
    if (!okay(AParcel_writeInt32(parcel, 0), "block type 0")) return false;
    if (!okay(AParcel_writeChar(parcel, u'\0'), "width placeholder")) return false;
    if (!okay(AParcel_writeChar(parcel, u'\0'), "height placeholder")) return false;
    const int32_t end = AParcel_getDataPosition(parcel);
    if (end <= begin || end - begin > 64) return false;
    if (!okay(AParcel_setDataPosition(parcel, begin), "rewind parcel")) return false;
    if (!okay(AParcel_writeInt32(parcel, end - begin), "write parcel size")) return false;
    return okay(AParcel_setDataPosition(parcel, end), "restore cursor");
}

// Parse AIDL response only after the NDK status header reports success.
// RetGetLdmBlockNum::writeToParcel (ELF 0x45755) writes int32, present marker,
// then a nested ST_LDM_BLOCK_NUM_INFO Parcelable.
bool readBlockNumReply(const AParcel* parcel) {
    AStatus* status = nullptr;
    if (!okay(AParcel_readStatusHeader(parcel, &status), "AIDL status header")) return false;
    if (status == nullptr) return false;
    const bool service_ok = AStatus_isOk(status);
    if (!service_ok) {
        std::fprintf(stderr, "SERVICE_REJECTED: exception=%d service_error=%d\n",
                     AStatus_getExceptionCode(status), AStatus_getServiceSpecificError(status));
        AStatus_delete(status);
        return false;
    }
    AStatus_delete(status);
    // Generated BpRender::GetLdmBlockNum first reads a nullable-return
    // parcelable presence marker, then RetGetLdmBlockNum::readFromParcel.
    // A successful response here began with 1; that is not a parcelable size.
    int32_t outer_present = 0;
    if (!okay(AParcel_readInt32(parcel, &outer_present), "return presence marker")) return false;
    if (outer_present != 1) {
        std::fprintf(stderr, "UNEXPECTED_RETURN_PRESENCE: %d\n", outer_present);
        return false;
    }
    int32_t length = 0, result = 0, present = 0, nested_length = 0, type = 0;
    char16_t width = 0, height = 0;
    if (!okay(AParcel_readInt32(parcel, &length), "result size")) return false;
    if (length < 12 || length > 128) {
        std::fprintf(stderr, "UNKNOWN_REPLY: outer size=%d\n", length);
        return false;
    }
    if (!okay(AParcel_readInt32(parcel, &result), "result field")) return false;
    if (!okay(AParcel_readInt32(parcel, &present), "presence field")) return false;
    std::printf("result_code=%d nested_present=%d\n", result, present);
    if (present != 1) { std::puts("No nested block dimensions returned."); return false; }
    if (!okay(AParcel_readInt32(parcel, &nested_length), "nested size")) return false;
    if (nested_length < 12 || nested_length > 128) {
        std::fprintf(stderr, "UNKNOWN_REPLY: nested size=%d\n", nested_length);
        return false;
    }
    if (!okay(AParcel_readInt32(parcel, &type), "reported type")) return false;
    if (!okay(AParcel_readChar(parcel, &width), "block width")) return false;
    if (!okay(AParcel_readChar(parcel, &height), "block height")) return false;
    const unsigned w = static_cast<unsigned>(width);
    const unsigned h = static_cast<unsigned>(height);
    std::printf("reported_type=%d width=%u height=%u product=%u\n", type, w, h, w*h);
    if (!w || !h || w>1000 || h>1000) {
        std::puts("UNVERIFIED: dimensions unusual; do not interpret as physical zones.");
        return false;
    }
    std::puts("READ_ONLY_QUERY_COMPLETED (dimensions not yet validated against hardware).");
    return true;
}

// MediaTek RetGetDeviceId::writeToParcel serializes exactly two int32 fields
// inside one nullable-sized parcelable: [return_present=1, size=12,
// return_code:int32, device_id:int32]. Device identifier is shown but NEVER
// reused automatically for hardware operations.
bool readDeviceIdReply(const AParcel* parcel) {
    AStatus* status = nullptr;
    if (!okay(AParcel_readStatusHeader(parcel, &status), "GetDeviceId AIDL status")) return false;
    if (status == nullptr) return false;
    const bool service_ok = AStatus_isOk(status);
    if (!service_ok) {
        std::fprintf(stderr, "DEVICE_ID_SERVICE_REJECTED: exception=%d service_error=%d\n",
                     AStatus_getExceptionCode(status), AStatus_getServiceSpecificError(status));
        AStatus_delete(status);
        return false;
    }
    AStatus_delete(status);
    int32_t present = 0, size = 0, result = 0, device_id = 0;
    if (!okay(AParcel_readInt32(parcel, &present), "GetDeviceId nullable marker")) return false;
    if (present != 1) {
        std::fprintf(stderr, "DEVICE_ID_REPLY_MISSING: present=%d\n", present);
        return false;
    }
    if (!okay(AParcel_readInt32(parcel, &size), "GetDeviceId parcelable size")) return false;
    if (size != 12) {
        std::fprintf(stderr, "DEVICE_ID_UNEXPECTED_REPLY_SIZE: %d\n", size);
        return false;
    }
    if (!okay(AParcel_readInt32(parcel, &result), "GetDeviceId result")) return false;
    if (!okay(AParcel_readInt32(parcel, &device_id), "GetDeviceId value")) return false;
    std::printf("device_result_code=%d device_id_signed=%d device_id_hex=0x%08x\n",
                result, device_id, static_cast<uint32_t>(device_id));
    if (result != 0) {
        std::puts("DEVICE_ID_QUERY_UNSUCCESSFUL (nonzero vendor result; do not reuse ID).");
        return false;
    }
    std::puts("DEVICE_ID_QUERY_COMPLETED (identifier not validated for LDM operations).");
    return true;
}

int run(bool query, bool deviceId, bool nativeSelector) {
    // ServiceManager symbol is part of Android's platform Binder ABI; it is
    // intentionally absent from the public NDK linker stubs.
    // Resolve at runtime instead of adding private SDK or copied libraries.
    void* libbinder = dlopen("libbinder_ndk.so", RTLD_NOW | RTLD_LOCAL);
    if (!libbinder) {
        std::fprintf(stderr, "BINDER_LIBRARY_UNAVAILABLE: %s\n", dlerror());
        return 2;
    }
    using CheckService = AIBinder* (*)(const char*);
    dlerror();
    void* symbol = dlsym(libbinder, "AServiceManager_checkService");
    if (!symbol) {
        std::fprintf(stderr, "SERVICE_MANAGER_SYMBOL_UNAVAILABLE: %s\n", dlerror());
        dlclose(libbinder);
        return 2;
    }
    const auto checkService = reinterpret_cast<CheckService>(symbol);
    AIBinder* binder = checkService(kService);
    if (binder == nullptr) {
        std::fprintf(stderr, "SERVICE_UNAVAILABLE: %s (could be SELinux or registration)\n", kService);
        return 2;
    }
    const AIBinder_Class* cls = AIBinder_Class_define(kDescriptor, onCreate, onDestroy, onTransact);
    if (cls == nullptr || !AIBinder_associateClass(binder, cls)) {
        std::fprintf(stderr, "BINDER_CLASS_FAILED\n");
        AIBinder_decStrong(binder);
        return 3;
    }
    if (!okay(AIBinder_ping(binder), "ping")) {
        AIBinder_decStrong(binder);
        return 4;
    }
    std::puts("RENDER_SERVICE_PING_OK");
    if (!query && !deviceId) { AIBinder_decStrong(binder); return 0; }

    AParcel* in = nullptr;
    AParcel* out = nullptr;
    int rc = 5;
    if (!okay(AIBinder_prepareTransaction(binder, &in), "prepare")) goto finish;
    if (deviceId) {
        // GetDeviceId is transaction 31 in the original MediaTek BpRender.
        // Query uses a single 32-bit input; it does not change display state.
        if (!okay(AParcel_writeInt32(in, 0), "GetDeviceId selector")) goto finish;
        if (!okay(AIBinder_transact(binder, kGetDeviceId, &in, &out, 0x10000000u),
                  "GetDeviceId (31)")) goto finish;
        if (out != nullptr && readDeviceIdReply(out)) rc = 0;
        goto finish;
    }
    // Both modes invoke only GetLdmBlockNum (read transaction 147).
    // --read-block-num retains the previously tested selector 0.
    // --read-block-num-native uses a literal verified at two function entry
    // points in libmi3_hwc_hal.so, but its *meaning* is not documented.
    const int32_t selector = nativeSelector ? kNativeLdmSelector : 0;
    if (nativeSelector) {
        std::printf("EXPERIMENTAL_NATIVE_SELECTOR: signed=%d hex=0x%08x\n",
                    selector, static_cast<uint32_t>(selector));
    }
    if (!okay(AParcel_writeInt32(in, selector), "integer selector")) goto finish;
    // The generated MediaTek BpRender::GetLdmBlockNum writes a non-null
    // parcelable presence marker (int32 1) before the ST_LDM_BLOCK_NUM_INFO
    // bytes. Omitting it causes the service to reject the request parcel.
    if (!okay(AParcel_writeInt32(in, 1), "parcelable presence marker")) goto finish;
    if (!writeBlockNumRequest(in)) goto finish;
    // Flag observed in BpRender::GetLdmBlockNum. This is NOT oneway.
    if (!okay(AIBinder_transact(binder, kGetLdmBlockNum, &in, &out, 0x10000000u),
              "GetLdmBlockNum (147)")) goto finish;
    if (out != nullptr && readBlockNumReply(out)) rc = 0;
finish:
    // AIBinder_transact takes ownership of `in` and ordinarily nulls it.
    if (in != nullptr) AParcel_delete(in);
    if (out != nullptr) AParcel_delete(out);
    AIBinder_decStrong(binder);
    return rc;
}
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::puts("TCL Render Probe v0.3\nUsage: tcl_render_probe --ping | --read-device-id | --read-block-num | --read-block-num-native\n"
                  "Read-only Binder queries 31 and 147 only; native selector is experimental.");
        return argc == 1 ? 0 : 1;
    }
    if (std::strcmp(argv[1], "--ping") == 0) return run(false, false, false);
    if (std::strcmp(argv[1], "--read-device-id") == 0) return run(false, true, false);
    if (std::strcmp(argv[1], "--read-block-num") == 0) return run(true, false, false);
    if (std::strcmp(argv[1], "--read-block-num-native") == 0) return run(true, false, true);
    std::fputs("Invalid mode. Use --ping, --read-device-id, --read-block-num, or --read-block-num-native.\n", stderr);
    return 1;
}
