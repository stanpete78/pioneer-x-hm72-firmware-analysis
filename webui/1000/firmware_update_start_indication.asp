<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><title>Network Setup</title><link href="../cmn.css" rel="stylesheet" type="text/css" /><script type="text/javascript" src="../js/cfg.js"></script><script type="text/javascript" src="../js/cmn.js"></script><script type="text/javascript" src="../js/mn_nolink.js"></script><script type="text/javascript" src="../js/fu.js"></script><script type="text/javascript">
<!--
window.onload = function() {
setTimeout("refresh()", 40000);
}
function refresh() {
window.top.location.href="http://<% aspGetIPAddr(-1); %>/bl_index.asp";
}
//-->
</script></head><body><table width="800" height="640" border="0" cellspacing="0" cellpadding="0" bgcolor="#e8e8f0"><tr><td align="left" valign="top" colspan="2"><img src="img/14AV_WebCon_PC_125.gif" alt="Network Setup" width="800" height="34" /></td></tr><tr><td valign="top" align="left"><script type="text/javascript">
<!--
write_setting_menu(MENU_ID_FIRMWARE_UPDATE, "<% aspGetCneVal("/cfg/Pioneer/State","Destination", "0"); %>", "<% aspCheckIfWired(-1); %>", "<% aspGetCneVal("/cfg/Networking/JBCONNECT","Enabled", "0"); %>", "<% aspGetInputInformationEx(); %>");
//-->
<% aspNotifyHostDM870UpdateStart(); %>
<% aspSetRebootInBSL(); %>
</script></td><td valign="top" align="left"><script type="text/javascript">
<!--
write_result_message("img/12AV_WebCon_PC_052.gif", start_indication_message("<% aspGetIPAddr(-1); %>"));
//-->
</script></td></tr><tr><td align="left" valign="bottom" colspan="2"><img src="img/14NetworkSetup_Copyright.gif" alt="Network Setup" width="800" height="31" /></td></tr></table></body></html>