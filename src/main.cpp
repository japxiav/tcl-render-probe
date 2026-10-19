// TCL Render Probe v0.1 - strictly whitelisted read-only AIDL client.
// Target: TCL C6K / MediaTek V643, Android 14. No privileged operations.
// Mode --ping: Binder ping only. Mode --read-block-num: AIDL transaction 147 only.
#include <android/binder_ibinder.h>
#include <android/binder_parcel.h>
#include <android/binder_status.h>
#include <cstdint>
#include <cstdio>
#include <cstring>

// AServiceManager_checkService is a stable Android API (since API 29),
// but binder_manager.h is a platform-only header not shipped in this NDK sysroot.
// Declare precisely the C ABI from AOSP; link via libbinder_ndk.
extern "C" AIBinder* AServiceManager_checkService(const char* instance);

namespace {
constexpr const char* kService = "vendor.mediatek.hardware.render.IRender/default";
constexpr const char* kDescriptor = "vendor.mediatek.hardware.render.IRender";
constexpr transaction_code_t kGetLdmBlockNum = 147;

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

int run(bool query) {
    AIBinder* binder = AServiceManager_checkService(kService);
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
    if (!query) { AIBinder_decStrong(binder); return 0; }

    AParcel* in = nullptr;
    AParcel* out = nullptr;
    int rc = 5;
    if (!okay(AIBinder_prepareTransaction(binder, &in), "prepare")) goto finish;
    // The first int32 and block_type=0 below are conservative test values,
    // not a manufacturer-confirmed semantic mapping. Only READ transaction 147.
    if (!okay(AParcel_writeInt32(in, 0), "integer selector")) goto finish;
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
        std::puts("TCL Render Probe v0.1\nUsage: tcl_render_probe --ping | --read-block-num\n"
                  "Only transaction 147 (GetLdmBlockNum) can be requested; no writes/root/firmware changes.");
        return argc == 1 ? 0 : 1;
    }
    if (std::strcmp(argv[1], "--ping") == 0) return run(false);
    if (std::strcmp(argv[1], "--read-block-num") == 0) return run(true);
    std::fputs("Invalid mode. Only --ping or --read-block-num is allowed.\n", stderr);
    return 1;
}
