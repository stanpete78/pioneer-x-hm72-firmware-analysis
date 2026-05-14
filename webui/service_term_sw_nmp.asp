<html xmlns="http://www.w3.org/1999/xhtml"><head><title>CommunicationSettings</title><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/><meta http-equiv="pragma" content="nocache" /><script language="JavaScript">
<!--
var attr_val_shell= 
{
"uart1":"UART1", 
"telnet":"TELNET", 
"current_setting":"<% aspGetCneVal("/cfg/CommunicationSettings","Shell",""); %>"
};

function writeFormShell()
{
document.write( "<form action='/goform/formHandlerConfigureCommunicationSettings' method='post' >" );
if( attr_val_shell.current_setting==attr_val_shell.telnet )
{
document.write( "<select name='Shell'><option value='" + attr_val_shell.uart1 + "'>" + attr_val_shell.uart1 + "</option><option value='" + attr_val_shell.telnet + "' selected='true'>" + attr_val_shell.telnet + "</option></select>" );
}
else
{
document.write( "<select name='Shell'><option value='" + attr_val_shell.uart1 + "' selected='true'>" + attr_val_shell.uart1 + "</option><option value='" + attr_val_shell.telnet + "'>" + attr_val_shell.telnet + "</option></select>" );
}
document.write( "<input type='submit' value='Apply' />" );
document.write( "</form>" );
}
//-->
</script></head><body><h2>CommunicationSettings</h2><h3>Shell</h3><script type="text/javascript">
<!--
writeFormShell();
//-->
</script></body></html>