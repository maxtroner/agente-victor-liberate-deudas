<?php
declare(strict_types=1); $secrets=is_file('/home/u628813570/.meta-secrets.php') ? (require '/home/u628813570/.meta-secrets.php') : []; require_once __DIR__ . '/../auth.php'; require_role('victor', 'tester'); require_csrf();
$data=json_decode(file_get_contents('php://input'),true) ?: $_POST; $phone=trim((string)($data['phone']??'')); $text=trim((string)($data['content']??''));
if (!preg_match('/^\+?[0-9]{8,20}$/',$phone)||$text==='') json_response(['error'=>'Datos invalidos'],422);
 $cfg=app_config(); $body=json_encode(['messaging_product'=>'whatsapp','to'=>$phone,'type'=>'text','text'=>['body'=>$text]]);
 $token=(string)($secrets['meta_token']??$cfg['meta_token']); $phone_id=(string)($secrets['meta_phone_id']??'1250371038140082'); $ch=curl_init('https://graph.facebook.com/v21.0/'.$phone_id.'/messages'); curl_setopt_array($ch,[CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>$body,CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$token,'Content-Type: application/json'],CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>15]); $result=curl_exec($ch); $code=curl_getinfo($ch,CURLINFO_HTTP_CODE); $curl_error=curl_error($ch); curl_close($ch);
if ($code<200||$code>=300) {
    error_log('WhatsApp reply failed HTTP '.$code.': '.($curl_error ?: $result));
    $meta_error = json_decode((string)$result, true)['error'] ?? [];
    json_response([
        'error' => 'Meta no acepto el mensaje',
        'detail' => (string)($meta_error['message'] ?? 'Respuesta no disponible'),
        'code' => (string)($meta_error['code'] ?? $code),
        'subcode' => (string)($meta_error['error_subcode'] ?? ''),
    ],502);
}
$stmt=db()->prepare('INSERT INTO conversations(phone,role,content) VALUES(?,?,?)'); $stmt->execute([$phone,'assistant',$text]); json_response(['status'=>'ok']);
