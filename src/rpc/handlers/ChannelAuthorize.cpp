#include <ripple/basics/StringUtilities.h>
#include <ripple/protocol/ErrorCodes.h>
#include <ripple/protocol/PayChan.h>
#include <ripple/protocol/STAccount.h>
#include <ripple/protocol/jss.h>
#include <ripple/resource/Fees.h>

#include <optional>
#include <rpc/RPCHelpers.h>

namespace RPC {

void
serializePayChanAuthorization(
    ripple::Serializer& msg,
    ripple::uint256 const& key,
    ripple::XRPAmount const& amt)
{
    msg.add32(ripple::HashPrefix::paymentChannelClaim);
    msg.addBitString(key);
    msg.add64(amt.drops());
}

Result
doChannelAuthorize(Context const& context)
{
    auto request = context.params;
    boost::json::object response = {};

    if (!request.contains("channel_id"))
        return Status{Error::rpcINVALID_PARAMS, "missingChannelID"};

    if (!request.at("channel_id").is_string())
        return Status{Error::rpcINVALID_PARAMS, "channelIDNotString"};

    if (!request.contains("amount"))
        return Status{Error::rpcINVALID_PARAMS, "missingAmount"};

    if (!request.at("amount").is_string())
        return Status{Error::rpcINVALID_PARAMS, "amountNotString"};

    if (!request.contains("key_type") && !request.contains("secret"))
        return Status{Error::rpcINVALID_PARAMS, "missingKeyTypeOrSecret"};

    auto v = keypairFromRequst(request);
    if (auto status = std::get_if<Status>(&v))
        return *status;

    auto const [pk, sk] =
        std::get<std::pair<ripple::PublicKey, ripple::SecretKey>>(v);

    ripple::uint256 channelId;
    if (!channelId.parseHex(request.at("channel_id").as_string().c_str()))
        return Status{Error::rpcCHANNEL_MALFORMED, "malformedChannelID"};

    auto optDrops = ripple::to_uint64(request.at("amount").as_string().c_str());

    if (!optDrops)
        return Status{Error::rpcCHANNEL_AMT_MALFORMED, "couldNotParseAmount"};

    std::uint64_t drops = *optDrops;

    ripple::Serializer msg;
    ripple::serializePayChanAuthorization(
        msg, channelId, ripple::XRPAmount(drops));

    try
    {
        auto const buf = ripple::sign(pk, sk, msg.slice());
        response["signature"] = ripple::strHex(buf);
    }
    catch (std::exception&)
    {
        return Status{Error::rpcINTERNAL};
    }

    return response;
}

}  // namespace RPC
