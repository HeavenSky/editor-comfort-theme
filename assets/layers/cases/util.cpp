#include <vector>
#include <string>
#define LIMIT 128

namespace util {
template <typename T>
class Buffer {
public:
    explicit Buffer(size_t n) : data_(n), size_(0) {}
    bool push(const T& v) {
        if (size_ >= LIMIT) return false;
        data_[size_++] = v;
        return true;
    }
private:
    std::vector<T> data_;
    size_t size_;
};
}  // namespace util
